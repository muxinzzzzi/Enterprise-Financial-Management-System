"""资产负债表生成器。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from models.financial_schemas import (
    BalanceSheetData,
    BalanceSheetItem,
    BalanceSheetRow,
    BalanceSheetTable,
    FinancialData,
    ReportConfig,
)

logger = logging.getLogger(__name__)


class BalanceSheetGenerator:
    """资产负债表生成器。"""

    def generate(self, financial_data: FinancialData, config: ReportConfig) -> BalanceSheetData:
        """生成资产负债表数据（从FinancialData）。
        
        Args:
            financial_data: 财务数据
            config: 报表配置
            
        Returns:
            BalanceSheetData: 资产负债表数据
        """
        account_balances = financial_data.account_balances
        classification = financial_data.account_classification

        # 构建资产项目
        assets = self._build_assets(account_balances, classification)

        # 构建负债项目
        liabilities = self._build_liabilities(account_balances, classification)

        # 构建所有者权益项目
        equity = self._build_equity(account_balances, classification)

        # 计算总计
        total_assets = self._calculate_total(assets)
        total_liabilities = self._calculate_total(liabilities)
        total_equity = self._calculate_total(equity)

        # 验证平衡关系
        is_balanced = abs(total_assets - (total_liabilities + total_equity)) < 0.01

        report_date = config.end_date or datetime.now()

        return BalanceSheetData(
            report_date=report_date,
            company_name=config.company_name,
            assets=assets,
            liabilities=liabilities,
            equity=equity,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            is_balanced=is_balanced,
        )

    def generate_from_dict(self, data: Dict[str, Any]) -> BalanceSheetTable:
        """从Python字典生成资产负债表表格数据。
        
        Args:
            data: 输入字典，结构如下：
                {
                    "assets": {
                        "current_assets": {
                            "现金": 100000.0,
                            "银行存款": 500000.0,
                            "应收账款": 200000.0,
                            ...
                        },
                        "non_current_assets": {
                            "固定资产": 1000000.0,
                            "无形资产": 200000.0,
                            ...
                        }
                    },
                    "liabilities": {
                        "current_liabilities": {
                            "应付账款": 150000.0,
                            "短期借款": 300000.0,
                            ...
                        },
                        "non_current_liabilities": {
                            "长期借款": 500000.0,
                            ...
                        }
                    },
                    "equity": {
                        "实收资本": 1000000.0,
                        "资本公积": 200000.0,
                        "盈余公积": 100000.0,
                        "未分配利润": 50000.0,
                        ...
                    }
                }
            
        Returns:
            BalanceSheetTable: 资产负债表表格数据
        """
        rows: List[BalanceSheetRow] = []
        asset_rows: List[BalanceSheetRow] = []
        liability_rows: List[BalanceSheetRow] = []
        equity_rows: List[BalanceSheetRow] = []

        # 处理资产部分
        assets_data = data.get("assets", {})
        current_assets = assets_data.get("current_assets", {})
        non_current_assets = assets_data.get("non_current_assets", {})

        # 流动资产
        current_assets_subtotal = 0.0
        asset_rows.append(BalanceSheetRow(item_name="流动资产", amount=0.0, level=0, is_subtotal=False, is_total=False))
        for item_name, amount in current_assets.items():
            asset_rows.append(
                BalanceSheetRow(item_name=item_name, amount=float(amount), level=1, is_subtotal=False, is_total=False)
            )
            current_assets_subtotal += float(amount)
        asset_rows.append(
            BalanceSheetRow(
                item_name="流动资产小计",
                amount=current_assets_subtotal,
                level=0,
                is_subtotal=True,
                is_total=False,
            )
        )

        # 非流动资产
        non_current_assets_subtotal = 0.0
        asset_rows.append(
            BalanceSheetRow(item_name="非流动资产", amount=0.0, level=0, is_subtotal=False, is_total=False)
        )
        for item_name, amount in non_current_assets.items():
            asset_rows.append(
                BalanceSheetRow(item_name=item_name, amount=float(amount), level=1, is_subtotal=False, is_total=False)
            )
            non_current_assets_subtotal += float(amount)
        asset_rows.append(
            BalanceSheetRow(
                item_name="非流动资产小计",
                amount=non_current_assets_subtotal,
                level=0,
                is_subtotal=True,
                is_total=False,
            )
        )

        # 资产合计
        total_assets = current_assets_subtotal + non_current_assets_subtotal
        asset_rows.append(
            BalanceSheetRow(
                item_name="资产合计", amount=total_assets, level=0, is_subtotal=False, is_total=True
            )
        )

        # 处理负债部分
        liabilities_data = data.get("liabilities", {})
        current_liabilities = liabilities_data.get("current_liabilities", {})
        non_current_liabilities = liabilities_data.get("non_current_liabilities", {})

        # 流动负债
        current_liabilities_subtotal = 0.0
        liability_rows.append(
            BalanceSheetRow(item_name="流动负债", amount=0.0, level=0, is_subtotal=False, is_total=False)
        )
        for item_name, amount in current_liabilities.items():
            liability_rows.append(
                BalanceSheetRow(item_name=item_name, amount=float(amount), level=1, is_subtotal=False, is_total=False)
            )
            current_liabilities_subtotal += float(amount)
        liability_rows.append(
            BalanceSheetRow(
                item_name="流动负债小计",
                amount=current_liabilities_subtotal,
                level=0,
                is_subtotal=True,
                is_total=False,
            )
        )

        # 非流动负债
        non_current_liabilities_subtotal = 0.0
        liability_rows.append(
            BalanceSheetRow(item_name="非流动负债", amount=0.0, level=0, is_subtotal=False, is_total=False)
        )
        for item_name, amount in non_current_liabilities.items():
            liability_rows.append(
                BalanceSheetRow(item_name=item_name, amount=float(amount), level=1, is_subtotal=False, is_total=False)
            )
            non_current_liabilities_subtotal += float(amount)
        liability_rows.append(
            BalanceSheetRow(
                item_name="非流动负债小计",
                amount=non_current_liabilities_subtotal,
                level=0,
                is_subtotal=True,
                is_total=False,
            )
        )

        # 负债合计
        total_liabilities = current_liabilities_subtotal + non_current_liabilities_subtotal
        liability_rows.append(
            BalanceSheetRow(
                item_name="负债合计", amount=total_liabilities, level=0, is_subtotal=False, is_total=True
            )
        )

        # 处理股东权益部分
        equity_data = data.get("equity", {})
        total_equity = 0.0
        equity_rows.append(
            BalanceSheetRow(item_name="股东权益", amount=0.0, level=0, is_subtotal=False, is_total=False)
        )
        for item_name, amount in equity_data.items():
            equity_rows.append(
                BalanceSheetRow(item_name=item_name, amount=float(amount), level=1, is_subtotal=False, is_total=False)
            )
            total_equity += float(amount)
        equity_rows.append(
            BalanceSheetRow(
                item_name="股东权益合计", amount=total_equity, level=0, is_subtotal=False, is_total=True
            )
        )

        # 负债和股东权益合计
        total_liabilities_and_equity = total_liabilities + total_equity

        # 验证平衡关系
        is_balanced = abs(total_assets - total_liabilities_and_equity) < 0.01

        # 合并所有行
        rows.extend(asset_rows)
        rows.extend(liability_rows)
        rows.extend(equity_rows)
        rows.append(
            BalanceSheetRow(
                item_name="负债和股东权益合计",
                amount=total_liabilities_and_equity,
                level=0,
                is_subtotal=False,
                is_total=True,
            )
        )

        return BalanceSheetTable(
            rows=rows,
            asset_rows=asset_rows,
            liability_rows=liability_rows,
            equity_rows=equity_rows,
            current_assets_subtotal=current_assets_subtotal,
            non_current_assets_subtotal=non_current_assets_subtotal,
            total_assets=total_assets,
            current_liabilities_subtotal=current_liabilities_subtotal,
            non_current_liabilities_subtotal=non_current_liabilities_subtotal,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            total_liabilities_and_equity=total_liabilities_and_equity,
            is_balanced=is_balanced,
        )

    def _build_assets(
        self, account_balances: dict[str, float], classification: dict[str, list[str]]
    ) -> List[BalanceSheetItem]:
        """构建资产项目。"""
        assets: List[BalanceSheetItem] = []
        asset_accounts = classification.get("assets", [])

        # 流动资产
        current_assets_items: List[BalanceSheetItem] = []
        current_asset_keywords = ["现金", "银行", "应收", "预付", "存货"]
        current_assets_total = 0.0

        for account in asset_accounts:
            amount = account_balances.get(account, 0.0)
            if amount != 0.0:
                account_lower = account.lower()
                if any(keyword in account_lower for keyword in current_asset_keywords):
                    current_assets_items.append(BalanceSheetItem(name=account, amount=amount))
                    current_assets_total += amount

        if current_assets_items:
            assets.append(
                BalanceSheetItem(name="流动资产", amount=current_assets_total, sub_items=current_assets_items)
            )

        # 非流动资产
        non_current_assets_items: List[BalanceSheetItem] = []
        non_current_assets_total = 0.0

        for account in asset_accounts:
            amount = account_balances.get(account, 0.0)
            if amount != 0.0:
                account_lower = account.lower()
                if not any(keyword in account_lower for keyword in current_asset_keywords):
                    non_current_assets_items.append(BalanceSheetItem(name=account, amount=amount))
                    non_current_assets_total += amount

        if non_current_assets_items:
            assets.append(
                BalanceSheetItem(
                    name="非流动资产", amount=non_current_assets_total, sub_items=non_current_assets_items
                )
            )

        return assets

    def _build_liabilities(
        self, account_balances: dict[str, float], classification: dict[str, list[str]]
    ) -> List[BalanceSheetItem]:
        """构建负债项目。"""
        liabilities: List[BalanceSheetItem] = []
        liability_accounts = classification.get("liabilities", [])

        # 流动负债
        current_liabilities_items: List[BalanceSheetItem] = []
        current_liability_keywords = ["应付", "预收", "应交"]
        current_liabilities_total = 0.0

        for account in liability_accounts:
            amount = account_balances.get(account, 0.0)
            if amount != 0.0:
                account_lower = account.lower()
                if any(keyword in account_lower for keyword in current_liability_keywords):
                    current_liabilities_items.append(BalanceSheetItem(name=account, amount=amount))
                    current_liabilities_total += amount

        if current_liabilities_items:
            liabilities.append(
                BalanceSheetItem(
                    name="流动负债", amount=current_liabilities_total, sub_items=current_liabilities_items
                )
            )

        # 非流动负债
        non_current_liabilities_items: List[BalanceSheetItem] = []
        non_current_liabilities_total = 0.0

        for account in liability_accounts:
            amount = account_balances.get(account, 0.0)
            if amount != 0.0:
                account_lower = account.lower()
                if not any(keyword in account_lower for keyword in current_liability_keywords):
                    non_current_liabilities_items.append(BalanceSheetItem(name=account, amount=amount))
                    non_current_liabilities_total += amount

        if non_current_liabilities_items:
            liabilities.append(
                BalanceSheetItem(
                    name="非流动负债",
                    amount=non_current_liabilities_total,
                    sub_items=non_current_liabilities_items,
                )
            )

        return liabilities

    def _build_equity(
        self, account_balances: dict[str, float], classification: dict[str, list[str]]
    ) -> List[BalanceSheetItem]:
        """构建所有者权益项目。"""
        equity: List[BalanceSheetItem] = []
        equity_accounts = classification.get("equity", [])

        equity_items: List[BalanceSheetItem] = []
        equity_total = 0.0

        for account in equity_accounts:
            amount = account_balances.get(account, 0.0)
            if amount != 0.0:
                equity_items.append(BalanceSheetItem(name=account, amount=amount))
                equity_total += amount

        if equity_items:
            equity.extend(equity_items)
        else:
            # 如果没有权益类科目，计算未分配利润
            # 未分配利润 = 资产 - 负债 - 其他权益
            equity.append(BalanceSheetItem(name="未分配利润", amount=equity_total))

        return equity

    def _calculate_total(self, items: List[BalanceSheetItem]) -> float:
        """计算项目总计。"""
        return sum(item.amount for item in items)


__all__ = ["BalanceSheetGenerator"]
