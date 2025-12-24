"""Markdown格式导出器。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from models.financial_schemas import (
    BalanceSheetData,
    BalanceSheetItem,
    CashFlowData,
    CashFlowItem,
    IncomeStatementData,
    IncomeStatementItem,
    ReportConfig,
)

logger = logging.getLogger(__name__)


class MarkdownExporter:
    """Markdown格式导出器。"""

    def export_balance_sheet(self, data: BalanceSheetData, config: ReportConfig) -> str:
        """导出资产负债表为Markdown格式。
        
        Args:
            data: 资产负债表数据
            config: 报表配置
            
        Returns:
            str: Markdown格式的报表内容
        """
        lines = []
        lines.append("# 资产负债表")
        lines.append("")

        # 报表基本信息
        if data.company_name:
            lines.append(f"**公司名称：** {data.company_name}")
        lines.append(f"**报表日期：** {data.report_date.strftime('%Y年%m月%d日')}")
        lines.append(f"**币种：** {config.currency}")
        lines.append("")

        # 资产部分
        lines.append("## 资产")
        lines.append("")
        lines.append("| 项目 | 金额 |")
        lines.append("|------|------|")

        for asset_item in data.assets:
            lines.append(f"| **{asset_item.name}** | {self._format_amount(asset_item.amount)} |")
            for sub_item in asset_item.sub_items:
                lines.append(f"| &nbsp;&nbsp;{sub_item.name} | {self._format_amount(sub_item.amount)} |")

        lines.append(f"| **资产总计** | **{self._format_amount(data.total_assets)}** |")
        lines.append("")

        # 负债部分
        lines.append("## 负债")
        lines.append("")
        lines.append("| 项目 | 金额 |")
        lines.append("|------|------|")

        for liability_item in data.liabilities:
            lines.append(f"| **{liability_item.name}** | {self._format_amount(liability_item.amount)} |")
            for sub_item in liability_item.sub_items:
                lines.append(f"| &nbsp;&nbsp;{sub_item.name} | {self._format_amount(sub_item.amount)} |")

        lines.append(f"| **负债总计** | **{self._format_amount(data.total_liabilities)}** |")
        lines.append("")

        # 所有者权益部分
        lines.append("## 所有者权益")
        lines.append("")
        lines.append("| 项目 | 金额 |")
        lines.append("|------|------|")

        for equity_item in data.equity:
            lines.append(f"| {equity_item.name} | {self._format_amount(equity_item.amount)} |")

        lines.append(f"| **所有者权益总计** | **{self._format_amount(data.total_equity)}** |")
        lines.append("")

        # 平衡验证
        lines.append("---")
        lines.append("")
        lines.append(f"**负债和所有者权益总计：** {self._format_amount(data.total_liabilities + data.total_equity)}")
        lines.append("")
        if data.is_balanced:
            lines.append("✅ **报表平衡**：资产 = 负债 + 所有者权益")
        else:
            lines.append(f"⚠️ **报表不平衡**：差异 {self._format_amount(abs(data.total_assets - (data.total_liabilities + data.total_equity)))}")
        lines.append("")

        return "\n".join(lines)

    def export_income_statement(self, data: IncomeStatementData, config: ReportConfig) -> str:
        """导出利润表为Markdown格式。
        
        Args:
            data: 利润表数据
            config: 报表配置
            
        Returns:
            str: Markdown格式的报表内容
        """
        lines = []
        lines.append("# 利润表")
        lines.append("")

        # 报表基本信息
        if data.company_name:
            lines.append(f"**公司名称：** {data.company_name}")
        lines.append(f"**报表期间：** {data.period_start.strftime('%Y年%m月%d日')} 至 {data.period_end.strftime('%Y年%m月%d日')}")
        lines.append(f"**币种：** {config.currency}")
        lines.append("")

        # 一、营业收入
        lines.append("## 一、营业收入")
        lines.append("")
        lines.append("| 项目 | 金额 |")
        lines.append("|------|------|")

        total_revenue = 0.0
        for revenue_item in data.revenue:
            lines.append(f"| {revenue_item.name} | {self._format_amount(revenue_item.amount)} |")
            total_revenue += revenue_item.amount

        lines.append(f"| **营业收入合计** | **{self._format_amount(total_revenue)}** |")
        lines.append("")


        # 三、营业费用
        if data.operating_expenses:
            lines.append("## 二、营业费用")
            lines.append("")
            lines.append("| 项目 | 金额 |")
            lines.append("|------|------|")

            total_expenses = 0.0
            for expense_item in data.operating_expenses:
                lines.append(f"| {expense_item.name} | {self._format_amount(expense_item.amount)} |")
                total_expenses += expense_item.amount

            lines.append(f"| **营业费用合计** | **{self._format_amount(total_expenses)}** |")
            lines.append("")

        # 四、营业利润
        lines.append("## 三、营业利润")
        lines.append("")
        lines.append(f"**营业利润：** {self._format_amount(data.operating_profit)}")
        lines.append("")

        # 五、利润总额
        lines.append("## 四、利润总额")
        lines.append("")
        lines.append(f"**利润总额：** {self._format_amount(data.total_profit)}")
        lines.append("")

        # 六、净利润
        lines.append("## 五、净利润")
        lines.append("")
        lines.append(f"**净利润：** {self._format_amount(data.net_profit)}")
        lines.append("")

        return "\n".join(lines)

    def export_cash_flow(self, data: CashFlowData, config: ReportConfig) -> str:
        """导出现金流量表为Markdown格式。
        
        Args:
            data: 现金流量表数据
            config: 报表配置
            
        Returns:
            str: Markdown格式的报表内容
        """
        lines = []
        lines.append("# 现金流量表")
        lines.append("")

        # 报表基本信息
        if data.company_name:
            lines.append(f"**公司名称：** {data.company_name}")
        lines.append(f"**报表期间：** {data.period_start.strftime('%Y年%m月%d日')} 至 {data.period_end.strftime('%Y年%m月%d日')}")
        lines.append(f"**币种：** {config.currency}")
        lines.append("")

        # 一、经营活动产生的现金流量
        lines.append("## 一、经营活动产生的现金流量")
        lines.append("")
        lines.append("| 项目 | 金额 |")
        lines.append("|------|------|")

        for item in data.operating_activities:
            lines.append(f"| {item.name} | {self._format_amount(item.amount)} |")

        operating_total = self._calculate_total(data.operating_activities)
        lines.append(f"| **经营活动产生的现金流量净额** | **{self._format_amount(operating_total)}** |")
        lines.append("")

        # 二、投资活动产生的现金流量
        lines.append("## 二、投资活动产生的现金流量")
        lines.append("")
        lines.append("| 项目 | 金额 |")
        lines.append("|------|------|")

        for item in data.investing_activities:
            lines.append(f"| {item.name} | {self._format_amount(item.amount)} |")

        investing_total = self._calculate_total(data.investing_activities)
        lines.append(f"| **投资活动产生的现金流量净额** | **{self._format_amount(investing_total)}** |")
        lines.append("")

        # 三、筹资活动产生的现金流量
        lines.append("## 三、筹资活动产生的现金流量")
        lines.append("")
        lines.append("| 项目 | 金额 |")
        lines.append("|------|------|")

        for item in data.financing_activities:
            lines.append(f"| {item.name} | {self._format_amount(item.amount)} |")

        financing_total = self._calculate_total(data.financing_activities)
        lines.append(f"| **筹资活动产生的现金流量净额** | **{self._format_amount(financing_total)}** |")
        lines.append("")

        # 四、现金净增加额
        lines.append("## 四、现金净增加额")
        lines.append("")
        lines.append(f"**现金净增加额：** {self._format_amount(data.net_cash_increase)}")
        lines.append("")

        # 五、期末现金余额
        lines.append("## 五、期末现金余额")
        lines.append("")
        lines.append(f"**期初现金余额：** {self._format_amount(data.beginning_cash_balance)}")
        lines.append(f"**现金净增加额：** {self._format_amount(data.net_cash_increase)}")
        lines.append(f"**期末现金余额：** {self._format_amount(data.ending_cash_balance)}")
        lines.append("")

        return "\n".join(lines)

    def _format_amount(self, amount: float) -> str:
        """格式化金额显示。"""
        if amount == 0.0:
            return "0.00"
        return f"{amount:,.2f}"

    def _calculate_total(self, items: List[CashFlowItem]) -> float:
        """计算项目总计。"""
        return sum(item.amount for item in items)


__all__ = ["MarkdownExporter"]
