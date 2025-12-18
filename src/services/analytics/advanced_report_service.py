"""高级报表生成服务。

整合三类报表生成器和AI关键点服务，提供统一的报表生成接口。
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm_client import LLMClient
from models.schemas import DocumentResult, PolicyFlag
from services.analytics.ai_report_services import DecisionSummaryService, IssueAttributionService
from services.analytics.report_generators import (
    AuditTrailReportGenerator,
    InvoiceAuditReportGenerator,
    PeriodSummaryReportGenerator,
)

logger = logging.getLogger(__name__)


class AdvancedReportService:
    """高级报表生成服务。"""

    def __init__(self, llm_client: LLMClient, output_dir: Optional[Path] = None) -> None:
        """初始化服务。
        
        Args:
            llm_client: LLM客户端
            output_dir: 报表输出目录，如果为None则不保存文件
        """
        self.llm = llm_client
        self.output_dir = output_dir

        # 初始化AI关键点服务
        self.decision_service = DecisionSummaryService(llm_client)
        self.issue_service = IssueAttributionService(llm_client)

        # 初始化报表生成器
        self.invoice_generator = InvoiceAuditReportGenerator(
            self.decision_service, self.issue_service
        )
        self.period_generator = PeriodSummaryReportGenerator(
            self.decision_service, self.issue_service
        )
        self.audit_trail_generator = AuditTrailReportGenerator(
            self.decision_service, self.issue_service
        )

    def generate_invoice_audit_report(
        self,
        document: DocumentResult,
        policy_flags: List[PolicyFlag],
        anomalies: List[str],
        duplicate_candidates: List[str],
        save_file: bool = True,
    ) -> str:
        """生成单张票据审核报告。
        
        Args:
            document: 票据结果
            policy_flags: 政策规则校验结果
            anomalies: 异常检测结果
            duplicate_candidates: 重复候选列表
            save_file: 是否保存为文件
            
        Returns:
            Markdown格式的报告内容
        """
        report = self.invoice_generator.generate(
            document, policy_flags, anomalies, duplicate_candidates
        )

        if save_file and self.output_dir:
            self._save_report(
                report,
                f"invoice_audit_{document.document_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            )

        return report

    def generate_period_summary_report(
        self,
        documents: List[DocumentResult],
        all_policy_flags: Dict[str, List[PolicyFlag]],
        all_anomalies: Dict[str, List[str]],
        all_duplicates: Dict[str, List[str]],
        period_type: str = "月",
        period_label: str = "",
        save_file: bool = True,
    ) -> str:
        """生成周期汇总报表。
        
        Args:
            documents: 票据列表
            all_policy_flags: 每个票据ID对应的政策规则列表
            all_anomalies: 每个票据ID对应的异常列表
            all_duplicates: 每个票据ID对应的重复候选列表
            period_type: 周期类型（月/周/项目）
            period_label: 周期标签（如"2025年10期"）
            save_file: 是否保存为文件
            
        Returns:
            Markdown格式的报告内容
        """
        report = self.period_generator.generate(
            documents, all_policy_flags, all_anomalies, all_duplicates, period_type, period_label
        )

        if save_file and self.output_dir:
            filename = f"period_summary_{period_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            # 清理文件名中的特殊字符
            filename = filename.replace("/", "_").replace("\\", "_")
            self._save_report(report, filename)

        return report

    def generate_audit_trail_report(
        self,
        documents: List[DocumentResult],
        all_policy_flags: Dict[str, List[PolicyFlag]],
        all_anomalies: Dict[str, List[str]],
        all_duplicates: Dict[str, List[str]],
        save_file: bool = True,
    ) -> str:
        """生成审计追溯与整改清单。
        
        Args:
            documents: 票据列表
            all_policy_flags: 每个票据ID对应的政策规则列表
            all_anomalies: 每个票据ID对应的异常列表
            all_duplicates: 每个票据ID对应的重复候选列表
            save_file: 是否保存为文件
            
        Returns:
            Markdown格式的报告内容
        """
        report = self.audit_trail_generator.generate(
            documents, all_policy_flags, all_anomalies, all_duplicates
        )

        if save_file and self.output_dir:
            self._save_report(
                report,
                f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            )

        return report

    def generate_all_reports(
        self,
        documents: List[DocumentResult],
        all_policy_flags: Dict[str, List[PolicyFlag]],
        all_anomalies: Dict[str, List[str]],
        all_duplicates: Dict[str, List[str]],
        period_type: str = "月",
        period_label: str = "",
        save_files: bool = True,
    ) -> Dict[str, str]:
        """生成所有三类报表。
        
        Returns:
            包含三类报表的字典，key为报告类型，value为Markdown内容
        """
        results = {}

        # 生成周期汇总报表
        results["period_summary"] = self.generate_period_summary_report(
            documents,
            all_policy_flags,
            all_anomalies,
            all_duplicates,
            period_type,
            period_label,
            save_files,
        )

        # 生成审计追溯与整改清单
        results["audit_trail"] = self.generate_audit_trail_report(
            documents, all_policy_flags, all_anomalies, all_duplicates, save_files
        )

        # 为每张票据生成审核报告（可选，如果票据数量不多）
        if len(documents) <= 50:  # 限制数量，避免生成过多报告
            invoice_reports = {}
            for doc in documents:
                policy_flags = all_policy_flags.get(doc.document_id, [])
                anomalies = all_anomalies.get(doc.document_id, [])
                duplicates = all_duplicates.get(doc.document_id, [])
                invoice_reports[doc.document_id] = self.generate_invoice_audit_report(
                    doc, policy_flags, anomalies, duplicates, save_files
                )
            results["invoice_reports"] = invoice_reports
        else:
            results["invoice_reports"] = {}  # 票据数量过多，不生成单张报告

        return results

    def _save_report(self, content: str, filename: str) -> None:
        """保存报告到文件。"""
        if not self.output_dir:
            return

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.output_dir / filename
            file_path.write_text(content, encoding="utf-8")
            logger.info(f"报表已保存: {file_path}")
        except Exception as e:
            logger.error(f"保存报表失败: {e}")


__all__ = ["AdvancedReportService"]
