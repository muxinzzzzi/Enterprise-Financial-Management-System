"""仪表盘统计模块。"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy import func

from database import db_session
from models.db_models import Document, LedgerEntry


class TrendPoint(TypedDict):
    date: str
    amount: float


class CategoryStat(TypedDict):
    category: str
    amount: float


class RiskStat(TypedDict):
    anomalies: int
    duplicates: int


class DashboardSummary(TypedDict):
    trend: List[TrendPoint]
    category_breakdown: List[CategoryStat]
    risk: RiskStat


def summary(days: int = 14, user_id: Optional[str] = None) -> DashboardSummary:
    """返回指定时间窗口内的趋势、分类汇总与风险统计。假设 created_at 为 UTC。"""
    days = max(1, days)
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days - 1)

    with db_session() as session:
        # 趋势：按天汇总金额
        day_expr = func.date(LedgerEntry.created_at)
        trend_query = (
            session.query(day_expr.label("day"), func.sum(LedgerEntry.amount))
            .filter(LedgerEntry.created_at >= start_date)
        )
        if user_id:
            trend_query = trend_query.filter(LedgerEntry.user_id == user_id)
        trend_rows = trend_query.group_by("day").order_by("day").all()
        trend: List[TrendPoint] = [
            {"date": row.day, "amount": float(row[1] or 0.0)}
            for row in trend_rows
        ]

        # 分类汇总：同一时间窗口
        category_query = (
            session.query(Document.category, func.sum(Document.amount))
            .filter(Document.created_at >= start_date)
        )
        if user_id:
            category_query = category_query.filter(Document.user_id == user_id)
        category_rows = (
            category_query.group_by(Document.category)
            .order_by(func.sum(Document.amount).desc())
            .all()
        )
        categories: List[CategoryStat] = [
            {"category": cat or "未分类", "amount": float(total or 0.0)}
            for cat, total in category_rows
        ]

        # 风险统计：同一时间窗口；为避免全量扫描，可后续用独立计数字段
        anomaly_query = (
            session.query(Document.raw_result)
            .filter(Document.created_at >= start_date)
        )
        if user_id:
            anomaly_query = anomaly_query.filter(Document.user_id == user_id)
        anomaly_rows = anomaly_query.all()
        anomaly_count = 0
        duplicate_count = 0
        for (record,) in anomaly_rows:
            if not isinstance(record, dict):
                continue
            anomaly_count += len(record.get("anomalies", []) or [])
            duplicate_count += len(record.get("duplicate_candidates", []) or [])

    return DashboardSummary(
        trend=trend,
        category_breakdown=categories,
        risk={"anomalies": int(anomaly_count), "duplicates": int(duplicate_count)},
    )


__all__ = ["summary"]
