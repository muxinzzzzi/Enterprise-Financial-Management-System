"""Pydantic 数据模型，描述对账系统输入输出。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class DocumentPayload(BaseModel):
    file_name: str
    file_content_base64: str = Field(description="前端上传的Base64内容（不含data URI前缀）")
    doc_type: Optional[str] = None
    vendor_hint: Optional[str] = None
    currency: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

    def document_id(self) -> str:
        return self.meta.get("document_id") or generate_id("doc")


class PolicyDocument(BaseModel):
    title: str
    content: str


class PipelineOptions(BaseModel):
    enable_duplicate_check: bool = True
    enable_policy_validation: bool = True
    enable_report: bool = True
    enable_learning: bool = True


class ReconciliationRequest(BaseModel):
    documents: List[DocumentPayload]
    policies: List[PolicyDocument] = Field(default_factory=list)
    options: PipelineOptions = Field(default_factory=PipelineOptions)
    user_id: Optional[int] = None


class OCRSpan(BaseModel):
    text: str
    confidence: float
    engine: str
    bbox: Dict[str, float] = Field(default_factory=dict)


class FieldValue(BaseModel):
    name: str
    value: Any
    confidence: float = 0.0
    source: str = ""


class PolicyFlag(BaseModel):
    rule_title: str
    severity: str
    message: str
    kind: str = "VIOLATION"
    references: List[str] = Field(default_factory=list)


class DocumentResult(BaseModel):
    document_id: str
    file_name: str
    vendor: Optional[str]
    currency: str
    total_amount: Optional[float]
    tax_amount: Optional[float]
    issue_date: Optional[str]
    category: Optional[str]
    structured_fields: Dict[str, Any]
    normalized_fields: Dict[str, Any]
    ocr_confidence: float
    ocr_spans: List[OCRSpan] = Field(default_factory=list)
    policy_flags: List[PolicyFlag] = Field(default_factory=list)
    anomalies: List[str] = Field(default_factory=list)
    duplicate_candidates: List[str] = Field(default_factory=list)
    reasoning_trace: List[str] = Field(default_factory=list)
    journal_entries: List[Dict[str, Any]] = Field(default_factory=list)


class AnalyticsRecord(BaseModel):
    """Analytics 缓存的结构化条目，保持字段一致性，便于二次利用。"""

    document_id: str
    vendor: Optional[str] = None
    category: Optional[str] = None
    currency: str = "CNY"
    amount: Optional[float] = None
    tax_amount: Optional[float] = None
    issue_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_document(cls, document: DocumentResult) -> "AnalyticsRecord":
        issue_dt: Optional[datetime] = None
        if document.issue_date:
            try:
                issue_dt = datetime.fromisoformat(document.issue_date)
            except ValueError:
                issue_dt = None
        return cls(
            document_id=document.document_id,
            vendor=document.vendor,
            category=document.category,
            currency=document.currency,
            amount=document.total_amount,
            tax_amount=document.tax_amount,
            issue_date=issue_dt,
        )

    def prompt_payload(self) -> Dict[str, Any]:
        """供提示词使用的 JSON-safe 表达。"""
        payload = self.model_dump(mode="json")
        if payload.get("issue_date"):
            payload["issue_date"] = str(payload["issue_date"]).split("T")[0]
        if payload.get("created_at"):
            payload["created_at"] = str(payload["created_at"]).replace("T", " ").split(".")[0]
        return payload


class AnalyticsInsight(BaseModel):
    question: str
    answer: str
    generated_sql: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReconciliationResponse(BaseModel):
    job_id: str = Field(default_factory=lambda: generate_id("job"))
    documents: List[DocumentResult]
    analytics: List[AnalyticsInsight]
    report: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsQueryRequest(BaseModel):
    question: str
    context_limit: int = 20


class FeedbackItem(BaseModel):
    document_id: str
    field_name: str
    old_value: Any
    new_value: Any
    comment: Optional[str] = None
    reviewer_id: Optional[str] = None
    importance: float = 0.5
    confidence: Optional[float] = None
    revision: Optional[int] = None


class FeedbackRequest(BaseModel):
    corrections: List[FeedbackItem]


class ReviewChange(BaseModel):
    field_name: str
    new_value: Any
    reason: str | None = None
    comment: str | None = None


class ReviewUpdateRequest(BaseModel):
    changes: List[ReviewChange]
    reviewer_id: str | None = None
    auto_approve: bool = False


class KnowledgeRulePayload(BaseModel):
    title: str
    content: str
    summary: str | None = None
    category: str | None = None
    tags: List[str] = Field(default_factory=list)
    risk_tags: List[str] = Field(default_factory=list)
    scope: List[str] = Field(default_factory=list)
    change_note: str | None = None


__all__ = [
    "AnalyticsRecord",
    "AnalyticsInsight",
    "AnalyticsQueryRequest",
    "DocumentPayload",
    "DocumentResult",
    "FeedbackRequest",
    "FieldValue",
    "OCRSpan",
    "PipelineOptions",
    "PolicyDocument",
    "PolicyFlag",
    "ReconciliationRequest",
    "ReconciliationResponse",
    "ReviewChange",
    "ReviewUpdateRequest",
    "KnowledgeRulePayload",
]
