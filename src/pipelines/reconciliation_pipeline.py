"""发票/单据OCR + 对账主流程。"""
from __future__ import annotations

import statistics
from typing import List

from models.schemas import (
    AnalyticsInsight,
    DocumentResult,
    PolicyFlag,
    ReconciliationRequest,
    ReconciliationResponse,
)
from services.analytics.anomaly_service import AnomalyDetectionService
from services.analytics.analytics_service import AnalyticsService
from services.extraction.categorization_service import ExpenseCategorizationService
from services.extraction.extraction_service import FieldExtractionService
from services.analytics.feedback_service import FeedbackService
from services.ingestion.ingestion_service import DocumentIngestionService
from services.extraction.normalization_service import NormalizationService
from services.ingestion.ocr_service import MultiEngineOCRService
from services.policy_rag.policy_service import PolicyValidationService
from services.analytics.report_service import ReportService


class ReconciliationPipeline:
    def __init__(
        self,
        ingestion: DocumentIngestionService,
        ocr: MultiEngineOCRService,
        extraction: FieldExtractionService,
        normalization: NormalizationService,
        policy: PolicyValidationService,
        categorization: ExpenseCategorizationService,
        anomaly: AnomalyDetectionService,
        analytics: AnalyticsService,
        feedback: FeedbackService,
        report: ReportService,
    ) -> None:
        self.ingestion = ingestion
        self.ocr = ocr
        self.extraction = extraction
        self.normalization = normalization
        self.policy = policy
        self.categorization = categorization
        self.anomaly = anomaly
        self.analytics_service = analytics
        self.feedback = feedback
        self.report_service = report

    def run(self, request: ReconciliationRequest) -> ReconciliationResponse:
        document_results: List[DocumentResult] = []

        if request.policies:
            self.policy.ingest_policies(request.policies)

        for payload in request.documents:
            ingestion_result = self.ingestion.ingest(payload)
            ocr_result = self.ocr.recognize(ingestion_result)
            schema = self.extraction.extract(ocr_result)
            normalized = self.normalization.normalize(schema, payload.meta)
            category = self.categorization.categorize(schema)
            policy_flags: List[PolicyFlag] = []
            if request.options.enable_policy_validation:
                policy_flags = self.policy.validate({**normalized, "document_id": payload.document_id()})
            anomaly_out = self.anomaly.analyze(payload.document_id(), normalized)

            document_results.append(
                DocumentResult(
                    document_id=payload.document_id(),
                    file_name=payload.file_name,
                    vendor=normalized.get("vendor_name"),
                    currency=normalized.get("currency") or "CNY",
                    total_amount=normalized.get("total_amount"),
                    tax_amount=normalized.get("tax_amount"),
                    issue_date=normalized.get("issue_date"),
                    category=category,
                    structured_fields=schema,
                    normalized_fields=normalized,
                    ocr_confidence=ocr_result.get("confidence", 0.0),
                    ocr_spans=ocr_result.get("spans", []),
                    policy_flags=policy_flags,
                    anomalies=anomaly_out["anomalies"],
                    duplicate_candidates=anomaly_out["duplicates"],
                    reasoning_trace=[
                        f"ingestion_layout={ingestion_result['layout']}",
                        f"ocr_confidence={ocr_result.get('confidence')}"
                    ],
                )
            )
        # Analytics & report

        self.analytics_service.sync(document_results)
        analytics = self._build_default_insights(document_results)
        report = self.report_service.generate(document_results) if request.options.enable_report else None

        return ReconciliationResponse(documents=document_results, analytics=analytics, report=report)

    def _build_default_insights(self, documents: List[DocumentResult]) -> List[AnalyticsInsight]:
        if not documents:
            return []
        amounts = [doc.total_amount for doc in documents if doc.total_amount]
        total = sum(amounts) if amounts else 0.0
        avg = statistics.mean(amounts) if amounts else 0.0
        return [
            AnalyticsInsight(
                question="本批次总金额?",
                answer=f"共处理{len(documents)}张单据，总金额约{total:.2f}",
                generated_sql="SELECT SUM(total_amount) FROM invoices WHERE batch=current_batch",
            ),
            AnalyticsInsight(
                question="平均单据金额?",
                answer=f"平均金额约{avg:.2f}",
                generated_sql="SELECT AVG(total_amount) FROM invoices WHERE batch=current_batch",
            ),
        ]


__all__ = ["ReconciliationPipeline"]
