"""财务报表服务主入口。"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from models.financial_schemas import (
    BalanceSheetData,
    CashFlowData,
    IncomeStatementData,
    ReportConfig,
    ReportResponse,
)
from services.financial_reports.ai_analyzer import AIAnalyzer
from services.financial_reports.data_aggregator import DataAggregator
from services.financial_reports.exporters.markdown_exporter import MarkdownExporter
from services.financial_reports.exporters.pdf_exporter import PDFExporter
from services.financial_reports.report_generators.balance_sheet import BalanceSheetGenerator
from services.financial_reports.report_generators.cash_flow import CashFlowGenerator
from services.financial_reports.report_generators.income_statement import IncomeStatementGenerator

logger = logging.getLogger(__name__)


class FinancialReportService:
    """财务报表服务。"""

    def __init__(self, llm_client=None) -> None:
        """初始化服务。
        
        Args:
            llm_client: LLM客户端，用于AI分析（可选）
        """
        self.data_aggregator = DataAggregator()
        self.balance_sheet_generator = BalanceSheetGenerator()
        self.income_statement_generator = IncomeStatementGenerator()
        self.cash_flow_generator = CashFlowGenerator()
        self.markdown_exporter = MarkdownExporter()
        self.pdf_exporter = PDFExporter()
        self.ai_analyzer = AIAnalyzer(llm_client=llm_client)

    def generate_balance_sheet(self, config: ReportConfig) -> ReportResponse:
        """生成资产负债表。
        
        Args:
            config: 报表配置
            
        Returns:
            ReportResponse: 报表响应
        """
        # 1. 聚合财务数据
        financial_data = self.data_aggregator.aggregate_ledger_data(
            start_date=config.start_date,
            end_date=config.end_date,
            user_id=config.user_id,
        )

        # 2. 生成报表数据
        report_data = self.balance_sheet_generator.generate(financial_data, config)

        # 3. 导出为Markdown
        markdown_content = self.markdown_exporter.export_balance_sheet(report_data, config)

        # 4. AI分析（如果启用）- 在PDF生成之前进行，以便合并到PDF中
        ai_analysis: Optional[str] = None
        if config.enable_ai_analysis:
            ai_analysis = self.ai_analyzer.analyze_balance_sheet(report_data)

        # 5. 导出为PDF（使用表格数据结构直接生成，包含AI分析）
        pdf_path: Optional[str] = None
        try:
            logger.debug("开始导出资产负债表为PDF")
            pdf_path = self.pdf_exporter.export_balance_sheet(report_data, config, ai_analysis=ai_analysis)
            if pdf_path:
                logger.info(f"资产负债表PDF导出成功: {pdf_path}")
            else:
                logger.warning("资产负债表PDF导出返回None，尝试markdown转换方式")
                # 如果直接导出失败，尝试从markdown转换
                if hasattr(self.pdf_exporter, 'export_balance_sheet_from_markdown'):
                    pdf_path = self.pdf_exporter.export_balance_sheet_from_markdown(markdown_content, config)
                    if pdf_path:
                        logger.info(f"使用markdown转换方式成功生成PDF: {pdf_path}")
        except Exception as e:
            logger.exception(f"PDF导出失败: {e}")
            # 如果直接导出失败，尝试从markdown转换
            if hasattr(self.pdf_exporter, 'export_balance_sheet_from_markdown'):
                try:
                    pdf_path = self.pdf_exporter.export_balance_sheet_from_markdown(markdown_content, config)
                    if pdf_path:
                        logger.info(f"使用markdown转换方式成功生成PDF: {pdf_path}")
                except Exception as e2:
                    logger.exception(f"markdown转换方式也失败: {e2}")

        return ReportResponse(
            report_type="balance_sheet",
            report_data=report_data.model_dump(),
            markdown_content=markdown_content,
            pdf_path=pdf_path,
            ai_analysis=ai_analysis,
        )

    def generate_income_statement(self, config: ReportConfig) -> ReportResponse:
        """生成利润表。
        
        Args:
            config: 报表配置
            
        Returns:
            ReportResponse: 报表响应
        """
        # 1. 聚合财务数据
        financial_data = self.data_aggregator.aggregate_ledger_data(
            start_date=config.start_date,
            end_date=config.end_date,
            user_id=config.user_id,
        )

        # 2. 生成报表数据
        report_data = self.income_statement_generator.generate(financial_data, config)

        # 3. 导出为Markdown
        markdown_content = self.markdown_exporter.export_income_statement(report_data, config)

        # 4. AI分析（如果启用）- 在PDF生成之前进行，以便合并到PDF中
        ai_analysis: Optional[str] = None
        if config.enable_ai_analysis:
            ai_analysis = self.ai_analyzer.analyze_income_statement(report_data)

        # 5. 导出为PDF（使用markdown转换方式）
        pdf_path: Optional[str] = None
        try:
            logger.debug("开始导出利润表为PDF")
            pdf_path = self.pdf_exporter.export_income_statement(markdown_content, config)
            if pdf_path:
                logger.info(f"利润表PDF导出成功: {pdf_path}")
            else:
                logger.warning("利润表PDF导出返回None")
        except Exception as e:
            logger.exception(f"利润表PDF导出失败: {e}")

        return ReportResponse(
            report_type="income_statement",
            report_data=report_data.model_dump(),
            markdown_content=markdown_content,
            pdf_path=pdf_path,
            ai_analysis=ai_analysis,
        )

    def generate_cash_flow(self, config: ReportConfig) -> ReportResponse:
        """生成现金流量表。
        
        Args:
            config: 报表配置
            
        Returns:
            ReportResponse: 报表响应
        """
        # 1. 聚合财务数据
        financial_data = self.data_aggregator.aggregate_ledger_data(
            start_date=config.start_date,
            end_date=config.end_date,
            user_id=config.user_id,
        )

        # 2. 生成报表数据
        report_data = self.cash_flow_generator.generate(financial_data, config)

        # 3. 导出为Markdown
        markdown_content = self.markdown_exporter.export_cash_flow(report_data, config)

        # 4. AI分析（如果启用）- 在PDF生成之前进行，以便合并到PDF中
        ai_analysis: Optional[str] = None
        if config.enable_ai_analysis:
            ai_analysis = self.ai_analyzer.analyze_cash_flow(report_data)

        # 5. 导出为PDF（使用markdown转换方式）
        pdf_path: Optional[str] = None
        try:
            logger.debug("开始导出现金流量表为PDF")
            pdf_path = self.pdf_exporter.export_cash_flow(markdown_content, config)
            if pdf_path:
                logger.info(f"现金流量表PDF导出成功: {pdf_path}")
            else:
                logger.warning("现金流量表PDF导出返回None")
        except Exception as e:
            logger.exception(f"现金流量表PDF导出失败: {e}")

        return ReportResponse(
            report_type="cash_flow",
            report_data=report_data.model_dump(),
            markdown_content=markdown_content,
            pdf_path=pdf_path,
            ai_analysis=ai_analysis,
        )

    def generate_all_reports(self, config: ReportConfig) -> Dict[str, ReportResponse]:
        """生成所有三类报表。
        
        Args:
            config: 报表配置
            
        Returns:
            Dict[str, ReportResponse]: 所有报表的响应字典
        """
        return {
            "balance_sheet": self.generate_balance_sheet(config),
            "income_statement": self.generate_income_statement(config),
            "cash_flow": self.generate_cash_flow(config),
        }


__all__ = ["FinancialReportService"]
