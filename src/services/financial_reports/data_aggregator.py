"""数据聚合器：从LedgerEntry汇总财务数据。"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from database import db_session
from models.db_models import LedgerEntry
from models.financial_schemas import FinancialData

logger = logging.getLogger(__name__)


class DataAggregator:
    """财务数据聚合器。"""

    # 会计科目分类规则
    ASSET_KEYWORDS = ["现金", "银行", "应收", "预付", "存货", "固定资产", "无形资产", "资产"]
    LIABILITY_KEYWORDS = ["应付", "预收", "借款", "负债", "应交"]
    EQUITY_KEYWORDS = ["实收资本", "资本公积", "盈余公积", "未分配利润", "权益", "所有者权益"]
    REVENUE_KEYWORDS = ["收入", "营业收入", "主营业务收入", "其他业务收入"]
    EXPENSE_KEYWORDS = ["费用", "成本", "营业成本", "管理费用", "销售费用", "财务费用", "支出"]

    def aggregate_ledger_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
    ) -> FinancialData:
        """汇总账务数据。
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            user_id: 用户ID，用于过滤数据
            
        Returns:
            FinancialData: 聚合后的财务数据
        """
        with db_session() as db:
            query = db.query(LedgerEntry)

            # 时间过滤
            if start_date:
                query = query.filter(LedgerEntry.created_at >= start_date)
            if end_date:
                query = query.filter(LedgerEntry.created_at <= end_date)

            # 用户过滤
            if user_id:
                query = query.filter(LedgerEntry.user_id == user_id)

            entries = query.all()

        # 计算科目余额
        account_balances = self.calculate_account_balances(entries, start_date, end_date)

        # 科目分类
        account_classification = self.classify_accounts(list(account_balances.keys()))

        # 计算借贷总额
        total_debit = sum(
            entry.amount for entry in entries if self._is_debit_account(entry.debit_account)
        )
        total_credit = sum(
            entry.amount for entry in entries if self._is_credit_account(entry.credit_account)
        )

        return FinancialData(
            account_balances=account_balances,
            account_classification=account_classification,
            period_start=start_date,
            period_end=end_date,
            total_debit=total_debit,
            total_credit=total_credit,
        )

    def calculate_account_balances(
        self,
        entries: List[LedgerEntry],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """计算科目余额。
        
        Args:
            entries: 会计分录列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, float]: 科目余额字典，key为科目名称，value为余额
        """
        balances: Dict[str, float] = defaultdict(float)

        for entry in entries:
            # 检查时间范围
            if start_date and entry.created_at < start_date:
                continue
            if end_date and entry.created_at > end_date:
                continue

            # 借方科目：增加余额
            debit_account = entry.debit_account
            if debit_account:
                balances[debit_account] += entry.amount

            # 贷方科目：减少余额（或根据科目性质调整）
            credit_account = entry.credit_account
            if credit_account:
                # 对于资产类科目，贷方减少余额
                # 对于负债和权益类科目，贷方增加余额
                if self._is_asset_account(credit_account):
                    balances[credit_account] -= entry.amount
                else:
                    balances[credit_account] += entry.amount

        return dict(balances)

    def classify_accounts(self, accounts: List[str]) -> Dict[str, List[str]]:
        """科目分类。
        
        Args:
            accounts: 科目名称列表
            
        Returns:
            Dict[str, List[str]]: 分类结果，key为类别，value为科目列表
        """
        classification: Dict[str, List[str]] = {
            "assets": [],
            "liabilities": [],
            "equity": [],
            "revenue": [],
            "expenses": [],
            "other": [],
        }

        for account in accounts:
            account_lower = account.lower()
            classified = False

            # 资产类
            if any(keyword in account_lower for keyword in self.ASSET_KEYWORDS):
                classification["assets"].append(account)
                classified = True

            # 负债类
            if not classified and any(keyword in account_lower for keyword in self.LIABILITY_KEYWORDS):
                classification["liabilities"].append(account)
                classified = True

            # 权益类
            if not classified and any(keyword in account_lower for keyword in self.EQUITY_KEYWORDS):
                classification["equity"].append(account)
                classified = True

            # 收入类
            if not classified and any(keyword in account_lower for keyword in self.REVENUE_KEYWORDS):
                classification["revenue"].append(account)
                classified = True

            # 费用类
            if not classified and any(keyword in account_lower for keyword in self.EXPENSE_KEYWORDS):
                classification["expenses"].append(account)
                classified = True

            # 其他
            if not classified:
                classification["other"].append(account)

        return classification

    def _is_asset_account(self, account: str) -> bool:
        """判断是否为资产类科目。"""
        account_lower = account.lower()
        return any(keyword in account_lower for keyword in self.ASSET_KEYWORDS)

    def _is_debit_account(self, account: str) -> bool:
        """判断借方科目。"""
        # 简化处理：资产、费用类科目通常在借方
        account_lower = account.lower()
        return any(keyword in account_lower for keyword in self.ASSET_KEYWORDS + self.EXPENSE_KEYWORDS)

    def _is_credit_account(self, account: str) -> bool:
        """判断贷方科目。"""
        # 简化处理：负债、权益、收入类科目通常在贷方
        account_lower = account.lower()
        return any(
            keyword in account_lower
            for keyword in self.LIABILITY_KEYWORDS + self.EQUITY_KEYWORDS + self.REVENUE_KEYWORDS
        )


__all__ = ["DataAggregator"]
