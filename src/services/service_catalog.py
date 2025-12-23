"""服务分层目录：在不改动现有逻辑的前提下，对 services 进行分组管理。

分组意图：
- ingestion：上传、预处理、OCR
- extraction：字段抽取、规范化、分类
- policy_rag：政策/规章的检索校验
- accounting：分录、凭证、总账、报表、税务、结账、验真/风控/成本中心
- analytics：异常、反馈、报表/仪表盘
- assistants：对话式助手、财务问答

说明：
- 仅做分组引用，未修改原有实现，便于后续路由或依赖注入统一管理。
- 可以在 app/pipeline 中按需使用这些分组来创建实例。
"""
from __future__ import annotations

from typing import Dict, List, Type

from services.accounting.ai_accountant import (
    AuditTrailService,
    AutoClosingEngine,
    ChatFinanceService,
    CostCenterClassifier,
    FinancialReportService,
    InvoiceVerificationService,
    LedgerEngine,
    RiskControlService,
    TaxEngine,
    VoucherService,
)
from services.analytics.analytics_service import AnalyticsService
from services.analytics.anomaly_service import AnomalyDetectionService
from services.analytics.dashboard_service import DashboardService
from services.analytics.feedback_service import FeedbackService
from services.analytics.report_service import ReportService
from services.assistants.assistant_service import AssistantService
from services.extraction.categorization_service import ExpenseCategorizationService
from services.extraction.extraction_service import FieldExtractionService
from services.extraction.normalization_service import NormalizationService
from services.ingestion.ingestion_service import DocumentIngestionService
from services.ingestion.ocr_service import MultiEngineOCRService
from services.policy_rag.policy_service import PolicyValidationService
from services.accounting.journal_service import JournalEntryService


def get_service_groups() -> Dict[str, List[Type]]:
    """返回分组后的服务类引用，供上层装配使用。"""
    return {
        "ingestion": [
            DocumentIngestionService,
            MultiEngineOCRService,
        ],
        "extraction": [
            FieldExtractionService,
            NormalizationService,
            ExpenseCategorizationService,
        ],
        "policy_rag": [
            PolicyValidationService,
        ],
        "accounting": [
            JournalEntryService,
            LedgerEngine,
            VoucherService,
            FinancialReportService,
            TaxEngine,
            AutoClosingEngine,
            InvoiceVerificationService,
            RiskControlService,
            CostCenterClassifier,
            AuditTrailService,
        ],
        "analytics": [
            AnomalyDetectionService,
            AnalyticsService,
            FeedbackService,
            DashboardService,
            ReportService,
        ],
        "assistants": [
            AssistantService,
            ChatFinanceService,
        ],
    }


__all__ = ["get_service_groups"]




