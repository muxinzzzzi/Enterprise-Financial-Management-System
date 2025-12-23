"""财务报表相关的数据模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportConfig(BaseModel):
    """报表配置。"""

    start_date: Optional[datetime] = Field(None, description="报表开始日期")
    end_date: Optional[datetime] = Field(None, description="报表结束日期")
    period_type: str = Field("month", description="报表期间类型：month/quarter/year")
    currency: str = Field("CNY", description="币种")
    user_id: Optional[str] = Field(None, description="用户ID，用于过滤数据")
    enable_ai_analysis: bool = Field(False, description="是否启用AI分析")
    company_name: Optional[str] = Field(None, description="公司名称")


class FinancialData(BaseModel):
    """财务数据聚合结果。"""

    account_balances: Dict[str, float] = Field(default_factory=dict, description="科目余额字典")
    account_classification: Dict[str, List[str]] = Field(
        default_factory=dict, description="科目分类：资产/负债/权益/收入/费用"
    )
    period_start: Optional[datetime] = Field(None, description="期间开始日期")
    period_end: Optional[datetime] = Field(None, description="期间结束日期")
    total_debit: float = Field(0.0, description="借方总额")
    total_credit: float = Field(0.0, description="贷方总额")


class BalanceSheetItem(BaseModel):
    """资产负债表项目。"""

    name: str = Field(..., description="项目名称")
    amount: float = Field(0.0, description="金额")
    sub_items: List["BalanceSheetItem"] = Field(default_factory=list, description="子项目")


class BalanceSheetRow(BaseModel):
    """资产负债表表格行。"""

    item_name: str = Field(..., description="项目名称")
    amount: float = Field(0.0, description="金额")
    level: int = Field(0, description="层级：0=主分类，1=子项目")
    is_subtotal: bool = Field(False, description="是否为小计行")
    is_total: bool = Field(False, description="是否为合计行")


class BalanceSheetTable(BaseModel):
    """资产负债表表格数据结构。"""

    rows: List[BalanceSheetRow] = Field(default_factory=list, description="表格行数据")
    asset_rows: List[BalanceSheetRow] = Field(default_factory=list, description="资产部分行")
    liability_rows: List[BalanceSheetRow] = Field(default_factory=list, description="负债部分行")
    equity_rows: List[BalanceSheetRow] = Field(default_factory=list, description="股东权益部分行")
    current_assets_subtotal: float = Field(0.0, description="流动资产小计")
    non_current_assets_subtotal: float = Field(0.0, description="非流动资产小计")
    total_assets: float = Field(0.0, description="资产合计")
    current_liabilities_subtotal: float = Field(0.0, description="流动负债小计")
    non_current_liabilities_subtotal: float = Field(0.0, description="非流动负债小计")
    total_liabilities: float = Field(0.0, description="负债合计")
    total_equity: float = Field(0.0, description="股东权益合计")
    total_liabilities_and_equity: float = Field(0.0, description="负债和股东权益合计")
    is_balanced: bool = Field(False, description="是否平衡")


class BalanceSheetData(BaseModel):
    """资产负债表数据。"""

    report_date: datetime = Field(..., description="报表日期")
    company_name: Optional[str] = Field(None, description="公司名称")
    assets: List[BalanceSheetItem] = Field(default_factory=list, description="资产项目")
    liabilities: List[BalanceSheetItem] = Field(default_factory=list, description="负债项目")
    equity: List[BalanceSheetItem] = Field(default_factory=list, description="所有者权益项目")
    total_assets: float = Field(0.0, description="资产总计")
    total_liabilities: float = Field(0.0, description="负债总计")
    total_equity: float = Field(0.0, description="所有者权益总计")
    is_balanced: bool = Field(False, description="是否平衡：资产=负债+所有者权益")


class IncomeStatementItem(BaseModel):
    """利润表项目。"""

    name: str = Field(..., description="项目名称")
    amount: float = Field(0.0, description="金额")
    sub_items: List["IncomeStatementItem"] = Field(default_factory=list, description="子项目")


class IncomeStatementData(BaseModel):
    """利润表数据。"""

    report_date: datetime = Field(..., description="报表日期")
    company_name: Optional[str] = Field(None, description="公司名称")
    period_start: datetime = Field(..., description="期间开始日期")
    period_end: datetime = Field(..., description="期间结束日期")
    revenue: List[IncomeStatementItem] = Field(default_factory=list, description="收入项目")
    cost_of_revenue: List[IncomeStatementItem] = Field(default_factory=list, description="营业成本项目")
    operating_expenses: List[IncomeStatementItem] = Field(default_factory=list, description="营业费用项目")
    operating_profit: float = Field(0.0, description="营业利润")
    total_profit: float = Field(0.0, description="利润总额")
    net_profit: float = Field(0.0, description="净利润")


class CashFlowItem(BaseModel):
    """现金流量表项目。"""

    name: str = Field(..., description="项目名称")
    amount: float = Field(0.0, description="金额")
    sub_items: List["CashFlowItem"] = Field(default_factory=list, description="子项目")


class CashFlowData(BaseModel):
    """现金流量表数据。"""

    report_date: datetime = Field(..., description="报表日期")
    company_name: Optional[str] = Field(None, description="公司名称")
    period_start: datetime = Field(..., description="期间开始日期")
    period_end: datetime = Field(..., description="期间结束日期")
    operating_activities: List[CashFlowItem] = Field(default_factory=list, description="经营活动现金流")
    investing_activities: List[CashFlowItem] = Field(default_factory=list, description="投资活动现金流")
    financing_activities: List[CashFlowItem] = Field(default_factory=list, description="筹资活动现金流")
    net_cash_increase: float = Field(0.0, description="现金净增加额")
    beginning_cash_balance: float = Field(0.0, description="期初现金余额")
    ending_cash_balance: float = Field(0.0, description="期末现金余额")


class ReportResponse(BaseModel):
    """报表生成响应。"""

    report_type: str = Field(..., description="报表类型：balance_sheet/income_statement/cash_flow")
    report_data: Dict[str, Any] = Field(..., description="报表数据（结构化）")
    markdown_content: str = Field("", description="Markdown格式的报表内容")
    pdf_path: Optional[str] = Field(None, description="PDF文件路径（如果已生成）")
    ai_analysis: Optional[str] = Field(None, description="AI分析内容（如果启用）")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")


class ReportRequest(BaseModel):
    """报表生成请求。"""

    report_type: str = Field(..., description="报表类型：balance_sheet/income_statement/cash_flow/all")
    config: ReportConfig = Field(..., description="报表配置")
    export_format: str = Field("markdown", description="导出格式：markdown/pdf")
    enable_ai_analysis: bool = Field(False, description="是否启用AI分析")


# 修复前向引用
BalanceSheetItem.model_rebuild()
IncomeStatementItem.model_rebuild()
CashFlowItem.model_rebuild()

__all__ = [
    "ReportConfig",
    "FinancialData",
    "BalanceSheetItem",
    "BalanceSheetData",
    "BalanceSheetRow",
    "BalanceSheetTable",
    "IncomeStatementItem",
    "IncomeStatementData",
    "CashFlowItem",
    "CashFlowData",
    "ReportResponse",
    "ReportRequest",
]
