"""现金流量表生成器。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from models.financial_schemas import CashFlowData, CashFlowItem, FinancialData, ReportConfig

logger = logging.getLogger(__name__)


class CashFlowGenerator:
    """现金流量表生成器。"""

    def generate(self, financial_data: FinancialData, config: ReportConfig) -> CashFlowData:
        """生成现金流量表数据。
        
        Args:
            financial_data: 财务数据
            config: 报表配置
            
        Returns:
            CashFlowData: 现金流量表数据
        """
        account_balances = financial_data.account_balances
        classification = financial_data.account_classification

        # 构建经营活动现金流
        operating_activities = self._build_operating_activities(account_balances, classification)

        # 构建投资活动现金流
        investing_activities = self._build_investing_activities(account_balances, classification)

        # 构建筹资活动现金流
        financing_activities = self._build_financing_activities(account_balances, classification)

        # 计算现金净增加额
        operating_total = self._calculate_total(operating_activities)
        investing_total = self._calculate_total(investing_activities)
        financing_total = self._calculate_total(financing_activities)
        net_cash_increase = operating_total + investing_total + financing_total

        # 期初和期末现金余额
        cash_accounts = [acc for acc in classification.get("assets", []) if "现金" in acc.lower() or "银行" in acc.lower()]
        beginning_cash_balance = 0.0  # 简化处理，假设期初为0
        ending_cash_balance = beginning_cash_balance + net_cash_increase

        # 如果有现金类科目，使用实际余额
        if cash_accounts:
            ending_cash_balance = sum(account_balances.get(acc, 0.0) for acc in cash_accounts)

        period_start = config.start_date or financial_data.period_start or datetime.now()
        period_end = config.end_date or financial_data.period_end or datetime.now()

        return CashFlowData(
            report_date=period_end,
            company_name=config.company_name,
            period_start=period_start,
            period_end=period_end,
            operating_activities=operating_activities,
            investing_activities=investing_activities,
            financing_activities=financing_activities,
            net_cash_increase=net_cash_increase,
            beginning_cash_balance=beginning_cash_balance,
            ending_cash_balance=ending_cash_balance,
        )

    def _build_operating_activities(
        self, account_balances: dict[str, float], classification: dict[str, list[str]]
    ) -> List[CashFlowItem]:
        """构建经营活动现金流。"""
        operating_activities: List[CashFlowItem] = []

        # 经营活动相关的科目
        operating_keywords = ["收入", "成本", "费用", "应收", "应付", "预收", "预付"]
        operating_items: List[CashFlowItem] = []

        # 收入类科目（现金流入）
        revenue_accounts = classification.get("revenue", [])
        for account in revenue_accounts:
            amount = account_balances.get(account, 0.0)
            if amount != 0.0:
                operating_items.append(CashFlowItem(name=f"销售商品、提供劳务收到的现金（{account}）", amount=amount))

        # 费用类科目（现金流出）
        expense_accounts = classification.get("expenses", [])
        for account in expense_accounts:
            amount = account_balances.get(account, 0.0)
            if amount != 0.0:
                operating_items.append(CashFlowItem(name=f"购买商品、接受劳务支付的现金（{account}）", amount=-amount))

        if operating_items:
            operating_activities.extend(operating_items)
        else:
            operating_activities.append(CashFlowItem(name="经营活动产生的现金流量净额", amount=0.0))

        return operating_activities

    def _build_investing_activities(
        self, account_balances: dict[str, float], classification: dict[str, list[str]]
    ) -> List[CashFlowItem]:
        """构建投资活动现金流。"""
        investing_activities: List[CashFlowItem] = []

        # 投资活动相关的科目
        investing_keywords = ["固定资产", "无形资产", "投资"]
        investing_items: List[CashFlowItem] = []

        asset_accounts = classification.get("assets", [])
        for account in asset_accounts:
            account_lower = account.lower()
            if any(keyword in account_lower for keyword in investing_keywords):
                amount = account_balances.get(account, 0.0)
                if amount != 0.0:
                    investing_items.append(CashFlowItem(name=f"购建固定资产、无形资产支付的现金（{account}）", amount=-amount))

        if investing_items:
            investing_activities.extend(investing_items)
        else:
            investing_activities.append(CashFlowItem(name="投资活动产生的现金流量净额", amount=0.0))

        return investing_activities

    def _build_financing_activities(
        self, account_balances: dict[str, float], classification: dict[str, list[str]]
    ) -> List[CashFlowItem]:
        """构建筹资活动现金流。"""
        financing_activities: List[CashFlowItem] = []

        # 筹资活动相关的科目
        financing_keywords = ["借款", "贷款", "实收资本", "资本公积"]
        financing_items: List[CashFlowItem] = []

        # 负债类科目（借款等）
        liability_accounts = classification.get("liabilities", [])
        for account in liability_accounts:
            account_lower = account.lower()
            if any(keyword in account_lower for keyword in ["借款", "贷款"]):
                amount = account_balances.get(account, 0.0)
                if amount != 0.0:
                    financing_items.append(CashFlowItem(name=f"取得借款收到的现金（{account}）", amount=amount))

        # 权益类科目（投资等）
        equity_accounts = classification.get("equity", [])
        for account in equity_accounts:
            account_lower = account.lower()
            if any(keyword in account_lower for keyword in ["实收资本", "资本公积"]):
                amount = account_balances.get(account, 0.0)
                if amount != 0.0:
                    financing_items.append(CashFlowItem(name=f"吸收投资收到的现金（{account}）", amount=amount))

        if financing_items:
            financing_activities.extend(financing_items)
        else:
            financing_activities.append(CashFlowItem(name="筹资活动产生的现金流量净额", amount=0.0))

        return financing_activities

    def _calculate_total(self, items: List[CashFlowItem]) -> float:
        """计算项目总计。"""
        return sum(item.amount for item in items)


__all__ = ["CashFlowGenerator"]
