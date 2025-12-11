"""AI 财务助手：结合数据库聚合与 LLM 回答。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy import func

from config import get_settings
from database import db_session
from llm_client import LLMClient
from models.db_models import AssistantLog, Document, LedgerEntry
from models.schemas import generate_id


class CategoryStat(TypedDict):
    category: str
    amount: float


class MonthlyStat(TypedDict):
    month: str
    amount: float


class LedgerSample(TypedDict):
    debit: str
    credit: str
    amount: float
    memo: Optional[str]
    created_at: str


class AssistantContext(TypedDict):
    total_amount: float
    currency: str
    period_days: int
    category_breakdown: List[CategoryStat]
    monthly_trend: List[MonthlyStat]
    ledger_samples: List[LedgerSample]


ASSISTANT_PROMPT = """
你是财务分析师，基于结构化数据直接回答。
必须使用中文 Markdown，禁止返回 JSON 或假设列表。

规则：
- 时间范围优先：如果问题没有写明季度/月份，请用一句话询问用户具体季度（例：“请确认要看的季度，例如 2025Q4？”），不要凭空假定。
- 当时间范围明确，或用户接受默认窗口时，用一句话给出结论，格式示例：
  - “{period_label}报销总额：<total> {currency}；差旅：<travel> {currency}”
- 若数据为空，直接说“当前统计窗口无有效数据”。
- 可选：如需要 SQL，追加一行以 `SQL:` 开头；不需要则省略。
- 默认统计窗口：最近 {period_days} 天。

结构化数据：{context}
用户问题：{question}
"""


class AssistantService:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client
        self.settings = get_settings()

    def query(self, question: str, user_id: Optional[str] = None, days: int = 120) -> Dict[str, Any]:
        context = self._build_context(user_id=user_id, days=days)
        prompt = ASSISTANT_PROMPT.format(
            context=json.dumps(context, ensure_ascii=False),
            question=question,
            currency=context["currency"],
            period_label=f"最近{days}天",
            period_days=days,
        )

        llm_meta: Dict[str, Any] = {"status": "ok"}
        answer: str
        start_ts = perf_counter()
        try:
            answer = self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": "你是专业财务分析助手，只能输出中文 Markdown 文本，禁止返回 JSON 或无依据的假设。",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=700,
            )
        except Exception as exc:  # noqa: BLE001
            answer = f"LLM 调用失败：{exc}"
            llm_meta.update({"status": "error", "error": str(exc)})
        llm_meta["latency_ms"] = int((perf_counter() - start_ts) * 1000)
        llm_meta["model"] = getattr(self.llm, "model", None)

        log_context = dict(context)
        log_context["llm_meta"] = llm_meta

        try:
            self._log(question=question, answer=answer, context=log_context, user_id=user_id)
        except Exception:
            # 日志失败不阻塞主流程
            pass

        return {"answer": answer, "context": context}

    def _build_context(self, user_id: Optional[str], days: int) -> AssistantContext:
        start_date = datetime.utcnow() - timedelta(days=days)
        with db_session() as session:
            doc_query = session.query(Document).filter(Document.created_at >= start_date)
            led_query = session.query(LedgerEntry).filter(LedgerEntry.created_at >= start_date)
            if user_id:
                doc_query = doc_query.filter(Document.user_id == user_id)
                led_query = led_query.filter(LedgerEntry.user_id == user_id)

            total = doc_query.with_entities(func.sum(Document.amount)).scalar() or 0.0

            category_rows = (
                doc_query.with_entities(Document.category, func.sum(Document.amount))
                .group_by(Document.category)
                .all()
            )

            month_expr = self._month_expr(session)
            monthly_rows = (
                doc_query.with_entities(month_expr.label("month"), func.sum(Document.amount))
                .group_by("month")
                .all()
            )

            ledger_rows = led_query.order_by(LedgerEntry.created_at.desc()).limit(10).all()

            currency_row = doc_query.with_entities(Document.currency).first()
            currency = (currency_row[0] if currency_row else None) or self.settings.default_currency

        return AssistantContext(
            total_amount=round(float(total), 2),
            currency=currency,
            period_days=days,
            category_breakdown=[
                {"category": cat or "未分类", "amount": float(val or 0.0)} for cat, val in category_rows
            ],
            monthly_trend=[{"month": month, "amount": float(val or 0.0)} for month, val in monthly_rows],
            ledger_samples=[
                {
                    "debit": row.debit_account,
                    "credit": row.credit_account,
                    "amount": row.amount,
                    "memo": row.memo,
                    "created_at": row.created_at.isoformat(),
                }
                for row in ledger_rows
            ],
        )

    def _month_expr(self, session) -> Any:
        """按方言选择月份截断表达式，默认 SQLite 使用 strftime。"""
        dialect = getattr(session.bind, "dialect", None)
        name = getattr(dialect, "name", "sqlite")
        if name == "postgresql":
            return func.to_char(Document.created_at, "YYYY-MM")
        if name == "mysql":
            return func.date_format(Document.created_at, "%Y-%m")
        return func.strftime("%Y-%m", Document.created_at)

    def _log(self, question: str, answer: str, context: Dict[str, Any], user_id: Optional[str]) -> None:
        with db_session() as session:
            log = AssistantLog(
                id=generate_id("ast"),
                question=question,
                answer=answer,
                context=context,
                user_id=user_id,
            )
            session.add(log)


__all__ = ["AssistantService"]
