"""AI 审核（Human-in-the-Loop）服务层。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

from database import db_session
from llm_client import LLMClient
from models.db_models import Document, ReviewLog
from models.schemas import (
    DocumentResult,
    FeedbackItem,
    FeedbackRequest,
    PolicyFlag,
    ReviewChange,
    ReviewUpdateRequest,
)
from services.analytics.advanced_report_service import AdvancedReportService
from services.policy_rag.policy_service import PolicyValidationService
from services.analytics.feedback_service import FeedbackService


class ReviewService:
    """封装 AI 审核队列、字段修订、审计报告与训练样本输出。"""

    def __init__(
        self,
        feedback_service: FeedbackService,
        report_service: AdvancedReportService,
        llm_client: LLMClient,
        policy_service: Optional[PolicyValidationService] = None,
    ) -> None:
        self.feedback = feedback_service
        self.report_service = report_service
        self.llm = llm_client
        self.policy_service = policy_service

    # ------------- 队列与详情 -------------
    def list_queue(self, status: str | None = None, q: str | None = None, limit: int = 50) -> List[Dict[str, Any]]:
        with db_session() as session:
            query = session.query(Document)
            if status:
                query = query.filter(Document.status == status)
            if q:
                like = f"%{q}%"
                query = query.filter(
                    (Document.file_name.ilike(like))
                    | (Document.vendor.ilike(like))
                    | (Document.category.ilike(like))
                )
            docs = query.order_by(Document.created_at.desc()).limit(limit).all()
            return [self._to_brief(doc) for doc in docs]

    def detail(self, doc_id: str) -> Dict[str, Any]:
        with db_session() as session:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                raise ValueError("票据不存在")

            # 若未存储过 RAG 结果，在线补一次；若已经跑过（policy_checked=True），即使为空也不重复耗时调用
            self._ensure_policy(session, doc)

            logs = (
                session.query(ReviewLog)
                .filter(ReviewLog.document_id == doc_id)
                .order_by(ReviewLog.created_at.desc())
                .all()
            )
            return self._to_detail(doc, logs)

    def backfill_policy(self, limit: int = 50) -> Dict[str, int]:
        """批量补跑未检查的票据，避免点击时长时间等待。"""
        updated = 0
        scanned = 0
        with db_session() as session:
            docs = session.query(Document).order_by(Document.created_at.desc()).all()
            for doc in docs:
                scanned += 1
                changed = self._ensure_policy(session, doc)
                if changed:
                    updated += 1
                if updated >= limit:
                    break
        return {"scanned": scanned, "updated": updated}

    def _ensure_policy(self, session, doc: Document) -> bool:
        """确保文档已有 policy_flags，返回是否更新。"""
        raw = doc.raw_result or {}
        checked_flag = raw.get("policy_checked")
        has_flags = bool(raw.get("policy_flags"))
        empty_flags = isinstance(raw.get("policy_flags"), list) and len(raw.get("policy_flags")) == 0

        # 若已标记且有有效 flags，不再调用 LLM
        if ((isinstance(checked_flag, bool) and checked_flag) or checked_flag in {1, "1", "true", "True"}) and has_flags:
            if checked_flag is not True:
                raw["policy_checked"] = True
                doc.raw_result = raw
                session.add(doc)
            return False

        # 已标记但 flags 为空，允许补跑一次
        if ((isinstance(checked_flag, bool) and checked_flag) or checked_flag in {1, "1", "true", "True"}) and empty_flags:
            pass  # 继续往下补跑

        # 未标记但已有 flags，直接补标记，避免重复耗时调用
        if has_flags and not checked_flag:
            raw["policy_checked"] = True
            doc.raw_result = raw
            session.add(doc)
            return True

        if not self.policy_service:
            raw["policy_checked"] = True
            doc.raw_result = raw
            session.add(doc)
            return True

        payload = raw.get("normalized_fields") or raw.get("structured_fields") or {}
        if not payload:
            payload = {
                "vendor_name": doc.vendor,
                "total_amount": doc.amount,
                "tax_amount": doc.tax_amount,
                "issue_date": raw.get("issue_date"),
                "category": doc.category,
            }
        debug = self.policy_service.validate_with_debug({**payload, "document_id": doc.id})
        raw["policy_flags"] = [f.model_dump() if hasattr(f, "model_dump") else dict(f) for f in debug.flags]
        raw["policy_hits"] = debug.hits
        raw["policy_reasoning"] = debug.reasoning
        raw["policy_checked"] = True  # 即使空也视为已检查
        doc.raw_result = raw
        session.add(doc)
        return True

    # ------------- 修改与批注 -------------
    def apply_changes(self, doc_id: str, request: ReviewUpdateRequest) -> Dict[str, Any]:
        if not request.changes:
            raise ValueError("缺少修改内容")

        with db_session() as session:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                raise ValueError("票据不存在")

            raw = doc.raw_result or {}
            normalized = raw.get("normalized_fields") or {}
            structured = raw.get("structured_fields") or {}
            history = raw.get("review_history") or []
            old_status = doc.status
            pending_status: str | None = None

            feedback_items: List[FeedbackItem] = []
            for change in request.changes:
                if change.field_name in {"status", "_status", "decision"}:
                    pending_status = str(change.new_value)
                    history.append(
                        {
                            "field_name": "_status",
                            "old_value": old_status,
                            "new_value": pending_status,
                            "reason": change.reason or "状态变更",
                            "comment": change.comment,
                            "reviewer_id": request.reviewer_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                    continue

                old_val = self._resolve_old_value(change, normalized, structured, raw)
                new_val = change.new_value
                self._assign_field(doc, normalized, raw, change.field_name, new_val)

                log = ReviewLog(
                    document_id=doc.id,
                    field_name=change.field_name,
                    old_value=None if old_val is None else str(old_val),
                    new_value=None if new_val is None else str(new_val),
                    reason=change.reason or change.comment,
                    reviewer_id=request.reviewer_id,
                    created_at=datetime.utcnow(),
                    meta={"comment": change.comment} if change.comment else None,
                )
                session.add(log)

                history.append(
                    {
                        "field_name": change.field_name,
                        "old_value": old_val,
                        "new_value": new_val,
                        "reason": change.reason,
                        "comment": change.comment,
                        "reviewer_id": request.reviewer_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

                feedback_items.append(
                    FeedbackItem(
                        document_id=doc.id,
                        field_name=change.field_name,
                        old_value=old_val,
                        new_value=new_val,
                        comment=change.reason or change.comment,
                        reviewer_id=request.reviewer_id,
                    )
                )

            raw["normalized_fields"] = normalized
            raw["review_history"] = history
            if pending_status:
                raw["status"] = pending_status
                doc.status = pending_status
            else:
                raw["status"] = "reviewing"
                doc.status = "reviewing"
            doc.raw_result = raw
            session.add(doc)

        # 写入反馈日志（并发安全）
        if feedback_items:
            self.feedback.record(FeedbackRequest(corrections=feedback_items), reviewer_id=request.reviewer_id)

        return self.detail(doc_id)

    def approve(self, doc_id: str, reviewer_id: str | None = None, comment: str | None = None) -> Dict[str, Any]:
        with db_session() as session:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                raise ValueError("票据不存在")
            raw = doc.raw_result or {}
            history = raw.get("review_history") or []
            history.append(
                {
                    "field_name": "_status",
                    "old_value": doc.status,
                    "new_value": "review_approved",
                    "reason": "一键审核通过",
                    "comment": comment,
                    "reviewer_id": reviewer_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            raw["review_history"] = history
            raw["status"] = "review_approved"
            doc.status = "review_approved"
            session.add(doc)
        return self.detail(doc_id)

    def batch_approve(self, doc_ids: List[str], reviewer_id: str | None = None) -> int:
        count = 0
        for doc_id in doc_ids:
            try:
                self.approve(doc_id, reviewer_id=reviewer_id)
                count += 1
            except Exception:
                continue
        return count

    # ------------- 报告与训练数据 -------------
    def generate_reports(self, doc_id: str) -> Dict[str, Any]:
        detail = self.detail(doc_id)
        doc_result = self._to_document_result(detail)

        policy_flags = [PolicyFlag(**flag) for flag in detail.get("policy_flags", []) if isinstance(flag, dict)]
        anomalies = detail.get("anomalies", [])
        duplicates = detail.get("duplicate_candidates", [])

        audit_report = self.report_service.generate_invoice_audit_report(
            doc_result, policy_flags, anomalies, duplicates, save_file=False
        )
        internal_report = self._internal_suggestion(detail)
        finance_report = self._finance_analysis(detail)

        return {
            "audit_report": audit_report,
            "internal_report": internal_report,
            "finance_report": finance_report,
        }

    def training_samples(self, limit: int = 10) -> List[str]:
        return self.feedback.few_shot_examples(limit=limit)

    # ------------- 辅助方法 -------------
    def _to_brief(self, doc: Document) -> Dict[str, Any]:
        raw = doc.raw_result or {}
        normalized = raw.get("normalized_fields") or {}
        structured = raw.get("structured_fields") or {}
        policy_flags = raw.get("policy_flags", []) or []
        anomalies = raw.get("anomalies", []) or []
        issue_date = raw.get("issue_date") or normalized.get("issue_date") or structured.get("issue_date")
        invoice_no = (
            normalized.get("invoice_number")
            or normalized.get("invoice_no")
            or structured.get("invoice_number")
            or structured.get("invoice_no")
        )
        return {
            "id": doc.id,
            "file_name": doc.file_name,
            "vendor": doc.vendor,
            "amount": doc.amount,
            "tax_amount": doc.tax_amount,
            "category": doc.category,
            "status": doc.status,
            "buyer": normalized.get("buyer_name") or normalized.get("title") or structured.get("buyer_name"),
            "invoice_no": invoice_no,
            "issue_date": issue_date,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "ocr_confidence": raw.get("ocr_confidence"),
            "policy_flags": len(policy_flags),
            "policy_flags_detail": policy_flags[:6],
            "anomalies": len(anomalies),
            "anomaly_tags": anomalies[:6],
            "risk_reasons": self._brief_risks(policy_flags, anomalies),
        }

    def _to_detail(self, doc: Document, logs: List[ReviewLog]) -> Dict[str, Any]:
        raw = doc.raw_result or {}
        normalized = raw.get("normalized_fields", {}) or {}
        structured = raw.get("structured_fields", {}) or {}
        return {
            "id": doc.id,
            "file_name": doc.file_name,
            "vendor": doc.vendor,
            "amount": doc.amount,
            "tax_amount": doc.tax_amount,
            "currency": doc.currency,
            "category": doc.category,
            "status": doc.status,
            "issue_date": raw.get("issue_date") or normalized.get("issue_date") or structured.get("issue_date"),
            "invoice_no": normalized.get("invoice_number")
            or normalized.get("invoice_no")
            or structured.get("invoice_number")
            or structured.get("invoice_no"),
            "buyer": normalized.get("buyer_name") or normalized.get("title") or structured.get("buyer_name"),
            "structured_fields": structured,
            "normalized_fields": normalized,
            "policy_flags": raw.get("policy_flags", []),
            "policy_hits": raw.get("policy_hits") or raw.get("rag_hits") or raw.get("retrieval_hits") or [],
            "policy_reasoning": raw.get("policy_reasoning") or raw.get("reasoning_trace") or [],
            "anomalies": raw.get("anomalies", []),
            "duplicate_candidates": raw.get("duplicate_candidates", []),
            "ocr_confidence": raw.get("ocr_confidence", 0.0),
            "ocr_text": raw.get("ocr_text") or raw.get("ocr_raw_text"),
            "review_history": raw.get("review_history", []),
            "review_logs": [
                {
                    "id": log.id,
                    "field_name": log.field_name,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "reason": log.reason,
                    "reviewer_id": log.reviewer_id,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
            "file_url": f"/api/v1/invoices/{doc.id}/file",
        }

    def _brief_risks(self, flags: List[Dict[str, Any]], anomalies: List[str]) -> List[str]:
        risks: List[str] = []
        for item in flags[:3]:
            if not isinstance(item, dict):
                continue
            title = item.get("rule_title") or item.get("message") or item.get("severity")
            if title:
                risks.append(str(title))
        for a in anomalies[:2]:
            if isinstance(a, str):
                risks.append(a)
        return risks

    def _resolve_old_value(self, change: ReviewChange, normalized: Dict[str, Any], structured: Dict[str, Any], raw: Dict[str, Any]) -> Any:
        if change.field_name in normalized:
            return normalized.get(change.field_name)
        if change.field_name in structured:
            return structured.get(change.field_name)
        return raw.get(change.field_name)

    def _assign_field(self, doc: Document, normalized: Dict[str, Any], raw: Dict[str, Any], field: str, value: Any) -> None:
        normalized[field] = value
        # 同步核心字段到主表，便于后续列表展示
        if field in {"vendor", "vendor_name"}:
            doc.vendor = value
        elif field in {"total_amount", "amount"}:
            try:
                doc.amount = float(value) if value is not None else None
            except Exception:
                doc.amount = None
        elif field == "tax_amount":
            try:
                doc.tax_amount = float(value) if value is not None else None
            except Exception:
                doc.tax_amount = None
        elif field == "category":
            doc.category = value
        elif field == "issue_date":
            raw["issue_date"] = value

    def _to_document_result(self, detail: Dict[str, Any]) -> DocumentResult:
        return DocumentResult(
            document_id=detail["id"],
            file_name=detail.get("file_name"),
            vendor=detail.get("vendor"),
            currency=detail.get("currency") or "CNY",
            total_amount=detail.get("amount"),
            tax_amount=detail.get("tax_amount"),
            issue_date=detail.get("issue_date"),
            category=detail.get("category"),
            structured_fields=detail.get("structured_fields") or {},
            normalized_fields=detail.get("normalized_fields") or {},
            ocr_confidence=detail.get("ocr_confidence") or 0.0,
            ocr_spans=[],
            policy_flags=[PolicyFlag(**flag) for flag in detail.get("policy_flags", []) if isinstance(flag, dict)],
            anomalies=detail.get("anomalies") or [],
            duplicate_candidates=detail.get("duplicate_candidates") or [],
            reasoning_trace=[],
            journal_entries=[],
        )

    def _internal_suggestion(self, detail: Dict[str, Any]) -> str:
        prompt = (
            "基于以下票据及人工修订记录，生成内部审计建议（<8条），突出流程改进与佐证材料补充。\n"
            f"票据信息: {detail.get('normalized_fields') or detail}\n"
            f"修订记录: {detail.get('review_history')}"
        )
        try:
            return self.llm.chat(
                [
                    {"role": "system", "content": "你是审计改进顾问，给出简洁可执行的建议列表。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=400,
                temperature=0.3,
            )
        except Exception:
            return "未启用 LLM，建议：补齐发票抬头、确保金额与实付一致、缺失字段请补充证明。"

    def _finance_analysis(self, detail: Dict[str, Any]) -> str:
        prompt = (
            "请对票据进行简短财务影响分析：金额、税额、科目匹配、可能的成本归集建议。"
            f"数据: {detail.get('normalized_fields') or detail}"
        )
        try:
            return self.llm.chat(
                [
                    {"role": "system", "content": "你是财务分析师，请简洁输出要点。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.25,
            )
        except Exception:
            return "未启用 LLM，建议检查税额比例、确认科目分类是否符合差旅/招待/采购等场景。"


__all__ = ["ReviewService"]




