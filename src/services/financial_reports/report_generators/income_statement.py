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
        classification = financial_data.account_classification

        # 构建收入项目
        revenue = self._build_revenue(account_balances, classification)

        # 构建营业成本项目
        cost_of_revenue = self._build_cost_of_revenue(account_balances, classification)

        # 构建营业费用项目
        operating_expenses = self._build_operating_expenses(account_balances, classification)

        # 计算营业利润
        total_revenue = self._calculate_total(revenue)
        total_cost = self._calculate_total(cost_of_revenue)
        total_expenses = self._calculate_total(operating_expenses)
        operating_profit = total_revenue - total_cost - total_expenses

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
            cost_of_revenue=cost_of_revenue,
            operating_expenses=operating_expenses,
            operating_profit=operating_profit,
            total_profit=total_profit,
            net_profit=net_profit,
        )

    def _build_revenue(
        self, account_balances: dict[str, float], classification: dict[str, list[str]]
    ) -> List[IncomeStatementItem]:
        """构建收入项目。"""
        revenue: List[IncomeStatementItem] = []
        revenue_accounts = classification.get("revenue", [])

        revenue_items: List[IncomeStatementItem] = []
        for account in revenue_accounts:
            amount = account_balances.get(account, 0.0)
            if amount != 0.0:
                revenue_items.append(IncomeStatementItem(name=account, amount=amount))

        if revenue_items:
            revenue.extend(revenue_items)
        else:
            # 如果没有收入类科目，添加默认项
            revenue.append(IncomeStatementItem(name="营业收入", amount=0.0))

        return revenue

    def _build_cost_of_revenue(
        self, account_balances: dict[str, float], classification: dict[str, list[str]]
    ) -> List[IncomeStatementItem]:
        """构建营业成本项目。"""
        cost_of_revenue: List[IncomeStatementItem] = []
        expense_accounts = classification.get("expenses", [])

        cost_keywords = ["成本", "营业成本", "主营业务成本"]
        cost_items: List[IncomeStatementItem] = []

        for account in expense_accounts:
            amount = account_balances.get(account, 0.0)
            if amount != 0.0:
                account_lower = account.lower()
                if any(keyword in account_lower for keyword in cost_keywords):
                    cost_items.append(IncomeStatementItem(name=account, amount=amount))

        if cost_items:
            cost_of_revenue.extend(cost_items)
        else:
            cost_of_revenue.append(IncomeStatementItem(name="营业成本", amount=0.0))

        return cost_of_revenue

    def _build_operating_expenses(
        self, account_balances: dict[str, float], classification: dict[str, list[str]]
    ) -> List[IncomeStatementItem]:
        """构建营业费用项目。"""
        operating_expenses: List[IncomeStatementItem] = []
        expense_accounts = classification.get("expenses", [])

        expense_keywords = ["费用", "管理费用", "销售费用", "财务费用"]
        expense_items: List[IncomeStatementItem] = []

        for account in expense_accounts:
            amount = account_balances.get(account, 0.0)
            if amount != 0.0:
                account_lower = account.lower()
                if any(keyword in account_lower for keyword in expense_keywords):
                    expense_items.append(IncomeStatementItem(name=account, amount=amount))

        if expense_items:
            operating_expenses.extend(expense_items)

        return operating_expenses

    def _calculate_total(self, items: List[IncomeStatementItem]) -> float:
        """计算项目总计。"""
        return sum(item.amount for item in items)


__all__ = ["IncomeStatementGenerator"]
