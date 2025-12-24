"""利润表生成器。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from models.financial_schemas import FinancialData, IncomeStatementData, IncomeStatementItem, ReportConfig

logger = logging.getLogger(__name__)


class IncomeStatementGenerator:
    """利润表生成器。"""

    def generate(self, financial_data: FinancialData, config: ReportConfig) -> IncomeStatementData:
        """生成利润表数据。
        
        Args:
            financial_data: 财务数据
            config: 报表配置
            
        Returns:
            IncomeStatementData: 利润表数据
        """
        account_balances = financial_data.account_balances
        entry_types = financial_data.account_entry_types

        # 构建收入项目
        revenue = self._build_revenue(account_balances, entry_types)

        # 构建营业费用（含所有 expense）
        operating_expenses = self._build_operating_expenses(account_balances, entry_types)

        total_revenue = self._calculate_total(revenue)
        total_expenses = self._calculate_total(operating_expenses)
        operating_profit = total_revenue - total_expenses

        # 利润总额（简化处理，假设没有营业外收支）
        total_profit = operating_profit

        # 净利润（简化处理，假设没有所得税）
        net_profit = total_profit

        period_start = config.start_date or financial_data.period_start or datetime.now()
        period_end = config.end_date or financial_data.period_end or datetime.now()

        return IncomeStatementData(
            report_date=period_end,
            company_name=config.company_name,
            period_start=period_start,
            period_end=period_end,
            revenue=revenue,
            cost_of_revenue=[],
            operating_expenses=operating_expenses,
            operating_profit=operating_profit,
            total_profit=total_profit,
            net_profit=net_profit,
        )

    def _build_revenue(
        self, account_balances: dict[str, float], entry_types: dict[str, str]
    ) -> List[IncomeStatementItem]:
        """构建收入项目。"""
        revenue: List[IncomeStatementItem] = []
        revenue_items: List[IncomeStatementItem] = []
        for account, entry_type in entry_types.items():
            if entry_type == "revenue":
                amount = account_balances.get(account, 0.0)
                if amount != 0.0:
                    revenue_items.append(IncomeStatementItem(name=account, amount=amount))

        if revenue_items:
            revenue.extend(revenue_items)
        else:
            revenue.append(IncomeStatementItem(name="营业收入", amount=0.0))

        return revenue

    def _build_operating_expenses(
        self, account_balances: dict[str, float], entry_types: dict[str, str]
    ) -> List[IncomeStatementItem]:
        """构建营业费用项目。"""
        operating_expenses: List[IncomeStatementItem] = []
        expense_items: List[IncomeStatementItem] = []

        for account, entry_type in entry_types.items():
            if entry_type != "revenue":
                amount = account_balances.get(account, 0.0)
                if amount != 0.0:
                    expense_items.append(IncomeStatementItem(name=account, amount=amount))

        if expense_items:
            operating_expenses.extend(expense_items)

        return operating_expenses

    def _calculate_total(self, items: List[IncomeStatementItem]) -> float:
        """计算项目总计。"""
        return sum(item.amount for item in items)


__all__ = ["IncomeStatementGenerator"]
