"""AI财务分析器。"""
from __future__ import annotations

import json
import logging
from typing import Optional

from llm_client import LLMClient
from models.financial_schemas import BalanceSheetData, CashFlowData, IncomeStatementData

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI财务分析器。"""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        """初始化AI分析器。
        
        Args:
            llm_client: LLM客户端，如果为None则尝试从环境创建
        """
        if llm_client is None:
            try:
                from llm_client import LLMClient as LLMClientType
                from config import get_settings
                settings = get_settings()
                self.llm_client = LLMClientType(
                    model=settings.llm_model,
                    api_key=settings.llm_api_key,
                    base_url=settings.llm_base_url
                )
            except Exception as e:
                logger.warning(f"无法初始化LLM客户端: {e}")
                self.llm_client = None
        else:
            self.llm_client = llm_client

    def analyze_balance_sheet(self, data: BalanceSheetData) -> str:
        """分析资产负债表。
        
        Args:
            data: 资产负债表数据
            
        Returns:
            str: AI分析报告（Markdown格式）
        """
        if not self.llm_client or not self.llm_client.enabled:
            logger.warning("LLM未配置，无法生成AI分析")
            return self._fallback_balance_sheet_analysis(data)

        try:
            # 构建分析数据
            analysis_data = {
                "company_name": data.company_name or "公司",
                "report_date": data.report_date.strftime('%Y年%m月%d日'),
                "total_assets": data.total_assets,
                "total_liabilities": data.total_liabilities,
                "total_equity": data.total_equity,
                "is_balanced": data.is_balanced,
                "assets": [
                    {
                        "name": item.name,
                        "amount": item.amount,
                        "sub_items": [{"name": sub.name, "amount": sub.amount} for sub in item.sub_items]
                    }
                    for item in data.assets
                ],
                "liabilities": [
                    {
                        "name": item.name,
                        "amount": item.amount,
                        "sub_items": [{"name": sub.name, "amount": sub.amount} for sub in item.sub_items]
                    }
                    for item in data.liabilities
                ],
                "equity": [
                    {
                        "name": item.name,
                        "amount": item.amount,
                        "sub_items": [{"name": sub.name, "amount": sub.amount} for sub in item.sub_items]
                    }
                    for item in data.equity
                ],
            }

            prompt = f"""请基于以下资产负债表数据，生成一份专业的财务分析报告。

要求：
1. 使用中文Markdown格式
2. 分析内容应包括：
   - 财务结构概况（资产、负债、权益的构成和比例）
   - 潜在风险（如负债率过高、流动性问题等）
   - 整体财务状况评价（健康度、发展趋势等）
3. 分析要客观、专业，基于数据给出具体建议

资产负债表数据：
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

请生成财务分析报告："""

            messages = [
                {
                    "role": "system",
                    "content": "你是一名资深的财务分析师，擅长分析企业财务报表。请用专业、客观的语言生成财务分析报告，使用Markdown格式。"
                },
                {"role": "user", "content": prompt}
            ]

            analysis = self.llm_client.chat(messages, max_tokens=1500, temperature=0.3)
            logger.info("资产负债表AI分析生成成功")
            return analysis

        except Exception as e:
            logger.exception(f"生成资产负债表AI分析失败: {e}")
            return self._fallback_balance_sheet_analysis(data)

    def analyze_income_statement(self, data: IncomeStatementData) -> str:
        """分析利润表。
        
        Args:
            data: 利润表数据
            
        Returns:
            str: AI分析报告（Markdown格式）
        """
        if not self.llm_client or not self.llm_client.enabled:
            logger.warning("LLM未配置，无法生成AI分析")
            return self._fallback_income_statement_analysis(data)

        try:
            # 构建分析数据
            analysis_data = {
                "company_name": data.company_name or "公司",
                "report_date": data.report_date.strftime('%Y年%m月%d日'),
                "period_start": data.period_start.strftime('%Y年%m月%d日'),
                "period_end": data.period_end.strftime('%Y年%m月%d日'),
                "operating_profit": data.operating_profit,
                "total_profit": data.total_profit,
                "net_profit": data.net_profit,
                "revenue": [
                    {
                        "name": item.name,
                        "amount": item.amount,
                        "sub_items": [{"name": sub.name, "amount": sub.amount} for sub in item.sub_items]
                    }
                    for item in data.revenue
                ],
                "cost_of_revenue": [
                    {
                        "name": item.name,
                        "amount": item.amount,
                        "sub_items": [{"name": sub.name, "amount": sub.amount} for sub in item.sub_items]
                    }
                    for item in data.cost_of_revenue
                ],
                "operating_expenses": [
                    {
                        "name": item.name,
                        "amount": item.amount,
                        "sub_items": [{"name": sub.name, "amount": sub.amount} for sub in item.sub_items]
                    }
                    for item in data.operating_expenses
                ],
            }

            prompt = f"""请基于以下利润表数据，生成一份专业的财务分析报告。

要求：
1. 使用中文Markdown格式
2. 分析内容应包括：
   - 财务结构概况（收入构成、成本结构、费用分布）
   - 潜在风险（如利润率下降、成本控制问题等）
   - 整体财务状况评价（盈利能力、经营效率等）
3. 分析要客观、专业，基于数据给出具体建议

利润表数据：
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

请生成财务分析报告："""

            messages = [
                {
                    "role": "system",
                    "content": "你是一名资深的财务分析师，擅长分析企业利润表。请用专业、客观的语言生成财务分析报告，使用Markdown格式。"
                },
                {"role": "user", "content": prompt}
            ]

            analysis = self.llm_client.chat(messages, max_tokens=1500, temperature=0.3)
            logger.info("利润表AI分析生成成功")
            return analysis

        except Exception as e:
            logger.exception(f"生成利润表AI分析失败: {e}")
            return self._fallback_income_statement_analysis(data)

    def analyze_cash_flow(self, data: CashFlowData) -> str:
        """分析现金流量表。
        
        Args:
            data: 现金流量表数据
            
        Returns:
            str: AI分析报告（Markdown格式）
        """
        if not self.llm_client or not self.llm_client.enabled:
            logger.warning("LLM未配置，无法生成AI分析")
            return self._fallback_cash_flow_analysis(data)

        try:
            # 构建分析数据
            analysis_data = {
                "company_name": data.company_name or "公司",
                "report_date": data.report_date.strftime('%Y年%m月%d日'),
                "period_start": data.period_start.strftime('%Y年%m月%d日'),
                "period_end": data.period_end.strftime('%Y年%m月%d日'),
                "net_cash_increase": data.net_cash_increase,
                "beginning_cash_balance": data.beginning_cash_balance,
                "ending_cash_balance": data.ending_cash_balance,
                "operating_activities": [
                    {
                        "name": item.name,
                        "amount": item.amount,
                        "sub_items": [{"name": sub.name, "amount": sub.amount} for sub in item.sub_items]
                    }
                    for item in data.operating_activities
                ],
                "investing_activities": [
                    {
                        "name": item.name,
                        "amount": item.amount,
                        "sub_items": [{"name": sub.name, "amount": sub.amount} for sub in item.sub_items]
                    }
                    for item in data.investing_activities
                ],
                "financing_activities": [
                    {
                        "name": item.name,
                        "amount": item.amount,
                        "sub_items": [{"name": sub.name, "amount": sub.amount} for sub in item.sub_items]
                    }
                    for item in data.financing_activities
                ],
            }

            prompt = f"""请基于以下现金流量表数据，生成一份专业的财务分析报告。

要求：
1. 使用中文Markdown格式
2. 分析内容应包括：
   - 财务结构概况（经营活动、投资活动、筹资活动的现金流情况）
   - 潜在风险（如现金流紧张、过度依赖筹资等）
   - 整体财务状况评价（现金流健康度、资金管理能力等）
3. 分析要客观、专业，基于数据给出具体建议

现金流量表数据：
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

请生成财务分析报告："""

            messages = [
                {
                    "role": "system",
                    "content": "你是一名资深的财务分析师，擅长分析企业现金流量表。请用专业、客观的语言生成财务分析报告，使用Markdown格式。"
                },
                {"role": "user", "content": prompt}
            ]

            analysis = self.llm_client.chat(messages, max_tokens=1500, temperature=0.3)
            logger.info("现金流量表AI分析生成成功")
            return analysis

        except Exception as e:
            logger.exception(f"生成现金流量表AI分析失败: {e}")
            return self._fallback_cash_flow_analysis(data)

    def _fallback_balance_sheet_analysis(self, data: BalanceSheetData) -> str:
        """资产负债表分析的回退方案。"""
        debt_ratio = (data.total_liabilities / data.total_assets * 100) if data.total_assets > 0 else 0
        equity_ratio = (data.total_equity / data.total_assets * 100) if data.total_assets > 0 else 0
        
        analysis = f"""## 财务结构概况

- **资产总计**: {data.total_assets:,.2f}
- **负债总计**: {data.total_liabilities:,.2f}
- **所有者权益总计**: {data.total_equity:,.2f}
- **资产负债率**: {debt_ratio:.2f}%
- **权益比率**: {equity_ratio:.2f}%

## 潜在风险

"""
        if debt_ratio > 70:
            analysis += "- ⚠️ **负债率偏高**：资产负债率超过70%，存在较高的财务风险\n"
        elif debt_ratio > 50:
            analysis += "- ⚠️ **负债率适中偏高**：资产负债率在50%-70%之间，需要关注负债结构\n"
        else:
            analysis += "- ✓ **负债率合理**：资产负债率在合理范围内\n"

        if not data.is_balanced:
            diff = abs(data.total_assets - (data.total_liabilities + data.total_equity))
            analysis += f"- ⚠️ **报表不平衡**：资产与负债+权益的差额为 {diff:,.2f}，需要检查数据准确性\n"

        analysis += f"""
## 整体财务状况评价

基于当前资产负债表数据，公司财务状况{'基本健康' if debt_ratio < 60 else '需要关注'}。建议定期监控财务指标变化。
"""
        return analysis

    def _fallback_income_statement_analysis(self, data: IncomeStatementData) -> str:
        """利润表分析的回退方案。"""
        total_revenue = sum(item.amount for item in data.revenue)
        total_cost = sum(item.amount for item in data.cost_of_revenue)
        gross_profit = total_revenue - total_cost
        gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
        net_margin = (data.net_profit / total_revenue * 100) if total_revenue > 0 else 0

        analysis = f"""## 财务结构概况

- **营业收入**: {total_revenue:,.2f}
- **营业成本**: {total_cost:,.2f}
- **营业利润**: {data.operating_profit:,.2f}
- **净利润**: {data.net_profit:,.2f}
- **毛利率**: {gross_margin:.2f}%
- **净利率**: {net_margin:.2f}%

## 潜在风险

"""
        if net_margin < 0:
            analysis += "- ⚠️ **净利润为负**：公司处于亏损状态，需要关注经营效率\n"
        elif net_margin < 5:
            analysis += "- ⚠️ **净利率偏低**：净利率低于5%，盈利能力需要提升\n"

        if gross_margin < 20:
            analysis += "- ⚠️ **毛利率偏低**：毛利率低于20%，成本控制需要加强\n"

        analysis += f"""
## 整体财务状况评价

基于当前利润表数据，公司盈利能力{'良好' if net_margin > 10 else '一般' if net_margin > 0 else '需要改善'}。建议关注成本控制和收入增长。
"""
        return analysis

    def _fallback_cash_flow_analysis(self, data: CashFlowData) -> str:
        """现金流量表分析的回退方案。"""
        operating_total = sum(item.amount for item in data.operating_activities)
        investing_total = sum(item.amount for item in data.investing_activities)
        financing_total = sum(item.amount for item in data.financing_activities)

        analysis = f"""## 财务结构概况

- **经营活动现金流**: {operating_total:,.2f}
- **投资活动现金流**: {investing_total:,.2f}
- **筹资活动现金流**: {financing_total:,.2f}
- **现金净增加额**: {data.net_cash_increase:,.2f}
- **期初现金余额**: {data.beginning_cash_balance:,.2f}
- **期末现金余额**: {data.ending_cash_balance:,.2f}

## 潜在风险

"""
        if operating_total < 0:
            analysis += "- ⚠️ **经营活动现金流为负**：经营活动无法产生正现金流，需要关注经营效率\n"

        if data.ending_cash_balance < 0:
            analysis += "- ⚠️ **期末现金余额为负**：公司可能存在资金链紧张问题\n"

        if financing_total > abs(operating_total) * 2:
            analysis += "- ⚠️ **过度依赖筹资**：筹资活动现金流远大于经营活动现金流，需要关注经营能力\n"

        analysis += f"""
## 整体财务状况评价

基于当前现金流量表数据，公司现金流状况{'健康' if operating_total > 0 and data.ending_cash_balance > 0 else '需要关注'}。建议加强现金流管理。
"""
        return analysis


__all__ = ["AIAnalyzer"]
