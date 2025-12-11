"""面向“AI 会计师”全链路的服务集合。

本文件集中放置新增模块，便于在 services 文件夹统一管理：
- 发票验真 / 风控 / 成本中心分类
- LedgerEngine（总账）与凭证生成器
- 财务报表 / 税务 / 结账 / 审计链 / 聊天助手

说明：
- 这里的实现是轻量可运行的骨架，便于后续替换为真实接口或数据库。
- 未侵入现有代码，可按需在 app/pipeline 中实例化使用。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from models.schemas import DocumentResult


# -------------------------
# 基础数据结构
# -------------------------
@dataclass
class LedgerLine:
    voucher_no: str
    date: dt.date
    debit_account: str
    credit_account: str
    amount: float
    memo: str
    currency: str = "CNY"
    cost_center: Optional[str] = None
    project_code: Optional[str] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    source_document_id: Optional[str] = None


@dataclass
class Voucher:
    voucher_no: str
    date: dt.date
    entries: List[LedgerLine]
    summary: str
    attachments: int = 1
    prepared_by: str = "system"
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    department: Optional[str] = None
    project_code: Optional[str] = None


# -------------------------
# 发票验真 & 风控 & 成本中心
# -------------------------
class InvoiceVerificationService:
    """发票验真、重复检测、基本一致性检查。"""

    def verify(self, document: DocumentResult, seen_hashes: set[str] | None = None) -> Dict[str, Any]:
        seen_hashes = seen_hashes or set()
        payload = json.dumps(document.model_dump(), ensure_ascii=False)
        md5 = hashlib.md5(payload.encode("utf-8")).hexdigest()  # noqa: S324

        checks: List[str] = []
        warnings: List[str] = []

        if md5 in seen_hashes:
            warnings.append("疑似重复报销")
        if document.total_amount and document.tax_amount and document.total_amount < document.tax_amount:
            warnings.append("价税不合理：税额大于合计")
        if document.issue_date:
            try:
                issue_dt = dt.date.fromisoformat(document.issue_date)
                if (dt.date.today() - issue_dt).days > 365:
                    warnings.append("跨年度报销，需特别审核")
            except ValueError:
                warnings.append("开票日期无法解析")

        checks.append("已计算 md5 用于重复检测")
        return {"md5": md5, "warnings": warnings, "checks": checks}


class RiskControlService:
    """预算/金额/跨部门等风险检查（示例规则，可扩展）。"""

    def run(self, document: DocumentResult, budget_rules: Dict[str, float] | None = None) -> List[Dict[str, Any]]:
        budget_rules = budget_rules or {}
        flags: List[Dict[str, Any]] = []
        category = document.category or "未分类"
        amount = float(document.total_amount or 0.0)
        if category in budget_rules and amount > budget_rules[category]:
            flags.append({"type": "budget_exceed", "category": category, "amount": amount})
        if amount <= 0:
            flags.append({"type": "amount_invalid", "category": category, "amount": amount})
        return flags


class CostCenterClassifier:
    """基于规则的轻量成本中心判定，可替换为 LLM/embedding。"""

    def classify(self, document: DocumentResult) -> Tuple[Optional[str], Optional[str]]:
        vendor = (document.vendor or "").lower()
        category = (document.category or "").lower()
        if any(k in vendor for k in ["滴滴", "高德", "出租", "出行"]):
            return "行政部-差旅", None
        if any(k in vendor for k in ["美团", "饿了么", "餐饮", "招待"]):
            return "市场部-招待", None
        if any(k in vendor for k in ["阿里", "腾讯云", "华为云", "aws"]):
            return "技术部-云平台", "云资源采购"
        if "固定资产" in category or "服务器" in category:
            return "技术部-设备", "资本化采购"
        return None, None


# -------------------------
# Ledger / Voucher / 报表
# -------------------------
class LedgerEngine:
    """内存版总账，便于演示；可替换为数据库实现。"""

    def __init__(self) -> None:
        self.lines: List[LedgerLine] = []

    def post(self, voucher: Voucher) -> None:
        self.lines.extend(voucher.entries)

    def balances(self) -> Dict[str, float]:
        bal: Dict[str, float] = {}
        for line in self.lines:
            bal[line.debit_account] = bal.get(line.debit_account, 0.0) + line.amount
            bal[line.credit_account] = bal.get(line.credit_account, 0.0) - line.amount
        return bal

    def list_lines(self) -> List[LedgerLine]:
        return list(self.lines)


class VoucherService:
    """根据分录生成完整凭证，补充编号/摘要/附件等信息。"""

    def build(self, document: DocumentResult, entries: List[Dict[str, Any]]) -> Voucher:
        voucher_no = f"V-{dt.date.today():%Y%m%d}-{uuid.uuid4().hex[:6]}"
        date = dt.date.today()
        memo = f"{document.vendor or document.file_name} 报销"
        lines = [
            LedgerLine(
                voucher_no=voucher_no,
                date=date,
                debit_account=e["debit_account"],
                credit_account=e["credit_account"],
                amount=float(e["amount"]),
                memo=e.get("memo") or memo,
                currency=e.get("currency", "CNY"),
                cost_center=e.get("cost_center"),
                project_code=e.get("project_code"),
                tax_rate=e.get("tax_rate"),
                tax_amount=e.get("tax_amount"),
                source_document_id=document.document_id,
            )
            for e in entries
            if e.get("amount")
        ]
        return Voucher(
            voucher_no=voucher_no,
            date=date,
            entries=lines,
            summary=memo,
            attachments=1,
            prepared_by="system",
            reviewed_by=None,
            approved_by=None,
            department=e.get("cost_center") if entries else None,  # type: ignore[index]
            project_code=e.get("project_code") if entries else None,  # type: ignore[index]
        )


class FinancialReportService:
    """基于 Ledger 生成简版报表（演示版）。"""

    def balance_sheet(self, ledger: LedgerEngine) -> Dict[str, Any]:
        bal = ledger.balances()
        assets = {k: v for k, v in bal.items() if any(x in k for x in ["现金", "银行", "应收", "固定资产"])}
        liabilities = {k: -v for k, v in bal.items() if "应付" in k or "贷款" in k}
        equity = sum(bal.values()) - sum(assets.values()) + sum(liabilities.values())
        return {"assets": assets, "liabilities": liabilities, "equity": equity}

    def income_statement(self, ledger: LedgerEngine) -> Dict[str, Any]:
        bal = ledger.balances()
        revenue = sum(-v for k, v in bal.items() if "收入" in k)
        expenses = sum(v for k, v in bal.items() if "费用" in k or "支出" in k)
        profit = revenue - expenses
        return {"revenue": revenue, "expenses": expenses, "profit": profit}

    def cashflow(self, ledger: LedgerEngine) -> Dict[str, Any]:
        bal = ledger.balances()
        operating = sum(v for k, v in bal.items() if "费用" in k)
        investing = sum(v for k, v in bal.items() if "固定资产" in k)
        financing = sum(-v for k, v in bal.items() if "贷款" in k)
        return {"operating": operating, "investing": investing, "financing": financing}

    def generate_summary(self, rows: List[Dict[str, Any]], period: str = "month", anchor_date: str | None = None) -> Dict[str, Any]:
        """
        rows: [{"account": "...", "amount": float, "memo": str, "date": "YYYY-MM-DD"}]
        period: month | quarter | year
        """
        anchor = dt.date.fromisoformat(anchor_date) if anchor_date else dt.date.today()
        if period == "year":
            start = dt.date(anchor.year, 1, 1)
        elif period == "quarter":
            q = (anchor.month - 1) // 3
            start = dt.date(anchor.year, q * 3 + 1, 1)
        else:
            start = dt.date(anchor.year, anchor.month, 1)
        end = anchor

        total_in = 0.0
        total_out = 0.0
        buckets: Dict[str, float] = {}
        for row in rows:
            try:
                dt_row = dt.date.fromisoformat(row.get("date", "1970-01-01"))
            except Exception:
                continue
            if not (start <= dt_row <= end):
                continue
            amt = float(row.get("amount", 0.0))
            acc = row.get("account", "其他")
            buckets[acc] = buckets.get(acc, 0.0) + amt
            if "收入" in acc or "应收" in acc:
                total_in += abs(amt)
            else:
                total_out += abs(amt)

        profit = total_in - total_out
        return {
            "period": period,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_in": round(total_in, 2),
            "total_out": round(total_out, 2),
            "profit": round(profit, 2),
            "buckets": {k: round(v, 2) for k, v in buckets.items()},
        }

    def narrative(self, summary: Dict[str, Any], llm: Any | None) -> str:
        if not llm or not getattr(llm, "enabled", False):
            return (
                f"期间 {summary['start_date']} 至 {summary['end_date']}：收入 {summary['total_in']:.2f}，"
                f"支出 {summary['total_out']:.2f}，利润 {summary['profit']:.2f}。"
            )
        prompt = (
            "请将以下财务摘要整理成一段简洁的中文报表，给出收入、支出、利润，并指出主要账户贡献。\n"
            f"{json.dumps(summary, ensure_ascii=False)}"
        )
        try:
            return llm.chat(
                [
                    {"role": "system", "content": "你是财务报表助手，用中文输出简洁段落。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=400,
                temperature=0.2,
            )
        except Exception:
            return (
                f"期间 {summary['start_date']} 至 {summary['end_date']}：收入 {summary['total_in']:.2f}，"
                f"支出 {summary['total_out']:.2f}，利润 {summary['profit']:.2f}。"
            )


# -------------------------
# 税务与结账
# -------------------------
class TaxEngine:
    """税务计算骨架，可接入实际税法规则/接口。"""

    def compute(self, document: DocumentResult) -> Dict[str, Any]:
        total = float(document.total_amount or 0.0)
        vat_rate = 0.06
        vat = round(total * vat_rate, 2)
        return {"vat": vat, "surtax": round(vat * 0.12, 2), "withholding": 0.0}


class AutoClosingEngine:
    """月末结账器：示例计提折旧/摊销/结转。"""

    def month_end_close(self, ledger: LedgerEngine) -> List[LedgerLine]:
        # 演示：不做真实分录，只返回待确认动作
        actions = [
            LedgerLine(
                voucher_no="auto-close",
                date=dt.date.today(),
                debit_account="管理费用-折旧费",
                credit_account="累计折旧",
                amount=0.0,
                memo="月末自动计提折旧（示例）",
            )
        ]
        return actions


# -------------------------
# 审计链与聊天助手
# -------------------------
class AuditTrailService:
    """记录审计事件链路。"""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def record(self, event: str, payload: Dict[str, Any]) -> None:
        self.events.append({"event": event, "payload": payload, "ts": dt.datetime.utcnow().isoformat()})

    def list_events(self) -> List[Dict[str, Any]]:
        return list(self.events)


class ChatFinanceService:
    """面向老板/财务的问答助手（演示版，基于本地汇总）。"""

    def __init__(self, ledger: LedgerEngine) -> None:
        self.ledger = ledger

    def query(self, question: str) -> Dict[str, Any]:
        # 这里只做规则化示例，后续可接入 LLM + SQL
        bal = self.ledger.balances()
        if "打车" in question or "差旅" in question:
            spend = sum(v for k, v in bal.items() if "差旅" in k)
            return {"answer": f"差旅相关支出约 {spend:.2f}"}
        if "利润" in question:
            report = FinancialReportService().income_statement(self.ledger)
            return {"answer": f"当前利润约 {report['profit']:.2f}"}
        return {"answer": "问题已收到，可接入 LLM/SQL 进一步实现。"}


__all__ = [
    "InvoiceVerificationService",
    "RiskControlService",
    "CostCenterClassifier",
    "LedgerEngine",
    "VoucherService",
    "FinancialReportService",
    "TaxEngine",
    "AutoClosingEngine",
    "AuditTrailService",
    "ChatFinanceService",
    "LedgerLine",
    "Voucher",
]
