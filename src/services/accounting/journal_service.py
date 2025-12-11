"""LLM生成会计凭证。"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from llm_client import LLMClient
from models.schemas import DocumentResult

logger = logging.getLogger(__name__)

# 行业/供应商规则库（可继续扩充）
VENDOR_RULES: Dict[str, Dict[str, str]] = {
    "滴滴": {"debit": "管理费用-差旅费", "credit": "银行存款", "cost_center": "行政部-差旅"},
    "高德": {"debit": "管理费用-差旅费", "credit": "银行存款", "cost_center": "行政部-差旅"},
    "美团": {"debit": "管理费用-业务招待费", "credit": "银行存款", "cost_center": "市场部-招待"},
    "饿了么": {"debit": "管理费用-业务招待费", "credit": "银行存款", "cost_center": "市场部-招待"},
    "京东": {"debit": "管理费用-办公费", "credit": "银行存款", "cost_center": "综合部-办公"},
    "阿里": {"debit": "研发支出-云服务费", "credit": "银行存款", "cost_center": "技术部-云平台"},
}

# 科目标准化映射（可结合数据库/embedding 做扩展）
ACCOUNT_NORMALIZATION_MAP: Dict[str, str] = {
    "差旅费": "管理费用-差旅费",
    "差旅费用": "管理费用-差旅费",
    "旅费": "管理费用-差旅费",
    "打车费": "管理费用-差旅费",
    "交通费": "管理费用-差旅费",
    "出租车费": "管理费用-差旅费",
    "办公费": "管理费用-办公费",
    "办公用品": "管理费用-办公费",
    "招待费": "管理费用-业务招待费",
    "招待费用": "管理费用-业务招待费",
    "云服务": "研发支出-云服务费",
    "服务器": "固定资产-电子设备",
}


@dataclass
class LedgerEntry:
    debit_account: str
    credit_account: str
    amount: float
    memo: str
    currency: str = "CNY"
    cost_center: Optional[str] = None
    project_code: Optional[str] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    explanation: Optional[str] = None


class JournalEntryService:
    """会计分录生成 + 校验 + 规则兜底。保持单文件实现，便于快速落地。"""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    # --------- Public API --------- #
    def generate(self, document: DocumentResult) -> List[Dict[str, Any]]:
        """主入口：先尝试 LLM 生成，失败或不平衡时回退规则模板。"""
        payload = self._build_payload(document)

        entries: List[LedgerEntry] = []
        explanation: str | None = None
        try:
            llm_result = self._call_llm(payload)
            entries = self._normalize_entries(llm_result.get("entries", []), document)
            explanation = llm_result.get("explanation") or llm_result.get("reason")
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM 分录生成失败，使用规则兜底: %s", exc)

        if not entries:
            entries = [self._rule_based_fallback(document)]
            explanation = explanation or "LLM 生成失败，使用规则兜底"

        entries = self._enforce_balance(entries)
        self._apply_default_meta(entries, document, explanation)
        return [entry.__dict__ for entry in entries]

    # --------- LLM 调用与提示 --------- #
    def _call_llm(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            "你是资深会计，请输出标准会计分录，严格 JSON：\n"
            "返回格式: {\"entries\": [{\"debit_account\": str, \"credit_account\": str, "
            "\"amount\": number, \"memo\": str, \"currency\": \"CNY\", "
            "\"cost_center\": str?, \"project_code\": str?, \"tax_rate\": number?, "
            "\"tax_amount\": number?, \"explanation\": str}], "
            "\"explanation\": str}\n"
            "- 借贷平衡，amount>0；不超过2-3条分录。\n"
            "- 结合提供的 vendor/category 提高科目准确率。\n"
            "- 必须是纯 JSON，无额外文本或 markdown。\n"
        )
        reply = self.llm.chat(
            [
                {"role": "system", "content": "你是资深会计，擅长中国会计准则，输出严格 JSON。"},
                {"role": "user", "content": prompt + "\n票据字段：" + json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(reply)
        except json.JSONDecodeError:
            # 容忍 LLM 在 response_format 下的异常格式
            return {"entries": [], "explanation": f"parse_error: {reply[:200]}"}  # type: ignore[list-item]

    def _build_payload(self, document: DocumentResult) -> Dict[str, Any]:
        return {
            "document_id": document.document_id,
            "vendor": document.vendor,
            "category": document.category,
            "currency": document.currency,
            "total_amount": document.total_amount,
            "tax_amount": document.tax_amount,
            "issue_date": document.issue_date,
            "file_name": document.file_name,
            "meta": document.normalized_fields or {},
        }

    # --------- 规则与校验 --------- #
    def _normalize_entries(self, raw_entries: List[Dict[str, Any]], document: DocumentResult) -> List[LedgerEntry]:
        normalized: List[LedgerEntry] = []
        for item in raw_entries:
            try:
                debit = self._normalize_account(str(item.get("debit_account", "")).strip())
                credit = self._normalize_account(str(item.get("credit_account", "")).strip())
                amount = float(item.get("amount", 0) or 0)
                if amount <= 0:
                    continue
                entry = LedgerEntry(
                    debit_account=debit or self._infer_debit(document),
                    credit_account=credit or "银行存款",
                    amount=amount,
                    memo=item.get("memo") or document.file_name,
                    currency=item.get("currency") or document.currency or "CNY",
                    cost_center=item.get("cost_center") or self._infer_cost_center(document),
                    project_code=item.get("project_code"),
                    tax_rate=self._safe_float(item.get("tax_rate")),
                    tax_amount=self._safe_float(item.get("tax_amount")),
                    explanation=item.get("explanation"),
                )
                normalized.append(entry)
            except Exception:
                continue
        return normalized

    def _enforce_balance(self, entries: List[LedgerEntry]) -> List[LedgerEntry]:
        if not entries:
            return entries
        total_debit = sum(e.amount for e in entries)
        total_credit = sum(e.amount for e in entries)
        diff = round(total_debit - total_credit, 2)
        if abs(diff) < 0.01:
            return entries
        # 轻量自修正：调整最后一条的金额
        target = entries[-1]
        target.amount = round(target.amount - diff, 2)
        return entries

    def _rule_based_fallback(self, document: DocumentResult) -> LedgerEntry:
        vendor = document.vendor or ""
        category = document.category or "管理费用-其他"
        rule = self._match_vendor_rule(vendor)
        debit = rule.get("debit") if rule else self._normalize_account(category)
        credit = rule.get("credit") if rule else "银行存款"
        return LedgerEntry(
            debit_account=debit or "管理费用-其他",
            credit_account=credit,
            amount=float(document.total_amount or document.tax_amount or 0.0),
            memo=document.file_name,
            currency=document.currency or "CNY",
            cost_center=rule.get("cost_center") if rule else self._infer_cost_center(document),
            explanation="规则兜底生成凭证",
        )

    # --------- 推断 & 工具函数 --------- #
    def _normalize_account(self, name: str) -> str:
        for k, v in ACCOUNT_NORMALIZATION_MAP.items():
            if k in name:
                return v
        return name or ""

    def _match_vendor_rule(self, vendor: str) -> Dict[str, str] | None:
        for k, v in VENDOR_RULES.items():
            if k in vendor:
                return v
        return None

    def _infer_debit(self, document: DocumentResult) -> str:
        rule = self._match_vendor_rule(document.vendor or "")
        if rule:
            return rule["debit"]
        return self._normalize_account(document.category or "管理费用-其他")

    def _infer_cost_center(self, document: DocumentResult) -> Optional[str]:
        vendor = (document.vendor or "").lower()
        if any(k in vendor for k in ["滴滴", "高德", "出租", "出行"]):
            return "行政部-差旅"
        if any(k in vendor for k in ["阿里", "腾讯云", "华为云", "aws"]):
            return "技术部-云平台"
        if any(k in vendor for k in ["美团", "饿了么"]):
            return "市场部-招待"
        return None

    def _apply_default_meta(self, entries: List[LedgerEntry], document: DocumentResult, explanation: Optional[str]) -> None:
        for entry in entries:
            if not entry.memo:
                entry.memo = document.file_name
            if explanation and not entry.explanation:
                entry.explanation = explanation

    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        try:
            return float(val)
        except Exception:
            return None


__all__ = ["JournalEntryService"]
