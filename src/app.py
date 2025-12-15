from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any, Dict
<<<<<<< HEAD
=======
from decimal import Decimal
from pathlib import Path
>>>>>>> 4fbaa5a (first commit)
from decimal import Decimal
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_cors import CORS

from config import DATA_DIR, get_settings
from database import init_db
from llm_client import LLMClient
from models.schemas import (
    AnalyticsQueryRequest,
    DocumentPayload,
    FeedbackRequest,
    PipelineOptions,
    PolicyDocument,
    ReconciliationRequest,
)
from pipelines.reconciliation_pipeline import ReconciliationPipeline
from repositories.audit_log import AuditLogger
from repositories.vector_store import VectorStore
from services.analytics.analytics_service import AnalyticsService
from services.analytics.anomaly_service import AnomalyDetectionService
from services.analytics.dashboard_service import summary as dashboard_summary
from services.analytics.feedback_service import FeedbackService
from services.assistants.assistant_service import AssistantService
from services.extraction.categorization_service import ExpenseCategorizationService
from services.extraction.extraction_service import FieldExtractionService
from services.extraction.normalization_service import NormalizationService
from services.ingestion.ingestion_service import DocumentIngestionService
from services.ingestion.ocr_service import MultiEngineOCRService
from services.accounting.journal_service import JournalEntryService
from services.policy_rag.policy_service import PolicyValidationService
from services.accounting.persistence_service import persist_results
from services.analytics.report_service import ReportService
from services.accounting.ai_accountant import FinancialReportService
from database import db_session
from models.db_models import Document, LedgerEntry
from services.user_service import (
    authenticate,
    create_user,
    get_user,
    list_users,
    login_or_register,
)
from utils.file_ops import save_base64_file
<<<<<<< HEAD
=======
from openpyxl import Workbook, load_workbook
from datetime import datetime
>>>>>>> 4fbaa5a (first commit)
from openpyxl import Workbook, load_workbook
from datetime import datetime


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

app = Flask(__name__)
CORS(app)
settings = get_settings()
init_db()
app.secret_key = os.getenv("APP_SECRET", "dev-secret")

llm_client = LLMClient(settings.llm_model, settings.llm_api_key, settings.llm_base_url)
vector_store = VectorStore()
journal_service = JournalEntryService(llm_client)
assistant_service = AssistantService(llm_client)
normalization_service = NormalizationService(settings=settings)
analytics_service = AnalyticsService(llm_client, cache_limit=settings.analytics_cache_limit)
financial_report_service = FinancialReportService()

services = {
    "ingestion": DocumentIngestionService(),
    "ocr": MultiEngineOCRService(llm_client),
    "extraction": FieldExtractionService(llm_client),
    "normalization": normalization_service,
    "policy": PolicyValidationService(vector_store, llm_client),
    "categorization": ExpenseCategorizationService(llm_client),
    "anomaly": AnomalyDetectionService(),
    "analytics": analytics_service,
    "feedback": FeedbackService(),
    "report": ReportService(llm_client),
}

pipeline = ReconciliationPipeline(**services)
audit_logger = AuditLogger(DATA_DIR / "cache" / "audit.log")
app_state: dict[str, Any] = {"last_result": None}


@app.get("/")
def root() -> Any:
    if session.get("user_id"):
        return redirect(url_for("dashboard_page"))
    return redirect(url_for("login_page"))


@app.get("/login")
def login_page() -> Any:
    if session.get("user_id"):
        return redirect(url_for("dashboard_page"))
    return render_template("login.html")


@app.get("/dashboard")
def dashboard_page() -> Any:
    if not session.get("user_id"):
        return redirect(url_for("login_page"))
    return render_template("dashboard.html")


@app.get("/health")
def health() -> Any:
    return jsonify(
        {
            "status": "ok",
            "env": settings.env,
            "llm_enabled": bool(settings.llm_api_key),
            "data_dir": str(DATA_DIR),
        }
    )


@app.post("/api/v1/reconciliations/run")
def run_pipeline() -> Any:
    data = request.get_json(force=True)
    payload = ReconciliationRequest(**data)
    result = pipeline.run(payload)
    for doc in result.documents:
        doc.journal_entries = journal_service.generate(doc)
    app_state["last_result"] = result
    audit_logger.log("pipeline_run", {"job_id": result.job_id, "doc_count": len(result.documents)})
    persist_results(result.documents, payload.documents)
    return jsonify(result.model_dump())


@app.post("/api/v1/reconciliations/upload")
def upload_and_run() -> Any:
    if "file" not in request.files:
        return jsonify({"success": False, "error": "缺少 file 字段"}), 400

    file_storage = request.files["file"]
    if not file_storage or not file_storage.filename:
        return jsonify({"success": False, "error": "文件无效"}), 400

    meta = _parse_form_json(request.form.get("meta"), default={})
    options_payload = _parse_form_json(request.form.get("options"), default={})
    policies_payload = _parse_form_json(request.form.get("policies"), default=[])

    raw_bytes = file_storage.read()
    if not raw_bytes:
        return jsonify({"success": False, "error": "文件内容为空"}), 400

    base64_content = base64.b64encode(raw_bytes).decode("utf-8")
    file_path = save_base64_file(file_storage.filename, base64_content, sub_dir="input/captures")
    meta["file_path"] = str(file_path)

    document_payload = DocumentPayload(
        file_name=file_storage.filename,
        file_content_base64=base64_content,
        meta=meta,
    )
    user_id_value = request.form.get("user_id")
    request_model = ReconciliationRequest(
        documents=[document_payload],
        policies=[PolicyDocument(**policy) for policy in policies_payload],
        options=PipelineOptions(**options_payload),
        user_id=int(user_id_value) if user_id_value else None,
    )

    result = pipeline.run(request_model)
    for doc in result.documents:
        doc.journal_entries = journal_service.generate(doc)
    app_state["last_result"] = result
    audit_logger.log(
        "upload_pipeline_run",
        {
            "job_id": result.job_id,
            "doc_count": len(result.documents),
            "file_name": file_storage.filename,
        },
    )
    persist_results(result.documents, request_model.documents)
    return jsonify(
        {
            "success": True,
            "job_id": result.job_id,
            "document": result.documents[0].model_dump() if result.documents else {},
            "report": result.report,
        }
    )


@app.get("/api/v1/invoices")
def list_invoices() -> Any:
    user_id = request.args.get("user_id")
    q = request.args.get("q", "")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
<<<<<<< HEAD
    with db_session() as session:
        query = session.query(Document)
        # 时间区间过滤（基于创建时间）
        if start_date:
            try:
                from datetime import datetime

                sd = datetime.fromisoformat(start_date)
                query = query.filter(Document.created_at >= sd)
            except Exception:
                pass
        if end_date:
            try:
                from datetime import datetime

                ed = datetime.fromisoformat(end_date)
                query = query.filter(Document.created_at <= ed)
            except Exception:
                pass
        if user_id:
            query = query.filter(Document.user_id == user_id)
        # 简单关键字搜索：文件名 / vendor / category / raw_result JSON 包含
        if q:
            like_q = f"%{q}%"
            query = query.filter(
                (Document.file_name.ilike(like_q))
                | (Document.vendor.ilike(like_q))
                | (Document.category.ilike(like_q))
            )
        query = query.order_by(Document.created_at.desc())
=======
    q = request.args.get("q", "")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    with db_session() as session:
        query = session.query(Document)
        # 时间区间过滤（基于创建时间）
        if start_date:
            try:
                from datetime import datetime

                sd = datetime.fromisoformat(start_date)
                query = query.filter(Document.created_at >= sd)
            except Exception:
                pass
        if end_date:
            try:
                from datetime import datetime

                ed = datetime.fromisoformat(end_date)
                query = query.filter(Document.created_at <= ed)
            except Exception:
                pass
        if user_id:
            query = query.filter(Document.user_id == user_id)
        # 简单关键字搜索：文件名 / vendor / category / raw_result JSON 包含
        if q:
            like_q = f"%{q}%"
            query = query.filter(
                (Document.file_name.ilike(like_q))
                | (Document.vendor.ilike(like_q))
                | (Document.category.ilike(like_q))
            )
        query = query.order_by(Document.created_at.desc())
>>>>>>> 4fbaa5a (first commit)
        docs = query.all()
        result = []
        for doc in docs:
            entries = [
                {
                    "id": le.id,
                    "debit_account": le.debit_account,
                    "credit_account": le.credit_account,
                    "amount": le.amount,
                    "memo": le.memo,
                    "created_at": le.created_at.isoformat(),
                }
                for le in doc.ledger_entries
            ]
            raw = doc.raw_result or {}
            # 尝试提取发票自身的开票/日期字段（可能在 raw 的不同位置）
            issue_date = None
            if isinstance(raw, dict):
                issue_date = raw.get("issue_date") or raw.get("normalized_fields", {}).get("issue_date")
                # 有时 issue_date 在 structured_fields 或 top-level 字段
                if not issue_date:
                    issue_date = raw.get("structured_fields", {}).get("issue_date")
<<<<<<< HEAD
=======
            # 尝试提取发票自身的开票/日期字段（可能在 raw 的不同位置）
            issue_date = None
            if isinstance(raw, dict):
                issue_date = raw.get("issue_date") or raw.get("normalized_fields", {}).get("issue_date")
                # 有时 issue_date 在 structured_fields 或 top-level 字段
                if not issue_date:
                    issue_date = raw.get("structured_fields", {}).get("issue_date")
>>>>>>> 4fbaa5a (first commit)
            voucher_path = raw.get("voucher_pdf_path")
            voucher_url = url_for("get_voucher_pdf", doc_id=doc.id) if voucher_path else None
            result.append(
                {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "vendor": doc.vendor,
                    "issue_date": issue_date,
<<<<<<< HEAD
=======
                    "issue_date": issue_date,
>>>>>>> 4fbaa5a (first commit)
                    "amount": doc.amount,
                    "tax_amount": doc.tax_amount,
                    "currency": doc.currency,
                    "category": doc.category,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat(),
                    "voucher_pdf_url": voucher_url,
                    "entries": entries,
                }
            )
    return jsonify({"success": True, "data": result})



@app.get("/api/v1/invoices/<doc_id>/file")
def get_invoice_file(doc_id: str) -> Any:
    """返回原始上传的发票文件以供预览/下载。"""
    with db_session() as session:
        doc = session.query(Document).filter_by(id=doc_id).first()
        if not doc:
            return jsonify({"success": False, "error": "not_found"}), 404
        path = doc.file_path
        if not path or not os.path.exists(path):
            return jsonify({"success": False, "error": "file_not_found"}), 404
        # 使用 send_file 返回原始文件（不作为附件，便于直接在浏览器预览）
        return send_file(path, as_attachment=False, download_name=doc.file_name)



@app.delete("/api/v1/invoices/<doc_id>")
def delete_invoice(doc_id: str) -> Any:
    """删除指定发票记录及其生成的凭证与原始文件（如存在）。"""
    with db_session() as session:
        doc = session.query(Document).filter_by(id=doc_id).first()
        if not doc:
            return jsonify({"success": False, "error": "not_found"}), 404
        # 删除相关文件：原始文件与凭证 PDF（若存在）
        try:
            raw = doc.raw_result or {}
            file_path = doc.file_path
            voucher_path = raw.get("voucher_pdf_path")
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            if voucher_path and os.path.exists(voucher_path):
                try:
                    os.remove(voucher_path)
                except Exception:
                    pass
        except Exception:
            pass
        # 删除数据库记录（ledger entries cascade 删除）
        session.delete(doc)
    return jsonify({"success": True})


@app.get("/api/v1/invoices/<doc_id>/voucher")
def get_voucher_pdf(doc_id: str) -> Any:
    with db_session() as session:
        doc = session.query(Document).filter_by(id=doc_id).first()
        if not doc:
            return jsonify({"success": False, "error": "not_found"}), 404
        raw = doc.raw_result or {}
        path = raw.get("voucher_pdf_path")
        if not path or not os.path.exists(path):
            return jsonify({"success": False, "error": "voucher_not_found"}), 404
        return send_file(path, as_attachment=True, download_name=f"{doc_id}.pdf")


@app.post("/api/v1/reports/financial")
def financial_report() -> Any:
    data = request.get_json(force=True)
    period = data.get("period_type", "month")  # month/quarter/year
    anchor = data.get("anchor_date")  # "2024-08-01"

    with db_session() as session:
        entries = session.query(LedgerEntry).all()
        rows = [
            {
                "account": f"{e.debit_account}/{e.credit_account}",
                "amount": e.amount,
                "memo": e.memo,
                "date": e.created_at.date().isoformat(),
            }
            for e in entries
        ]
    summary = financial_report_service.generate_summary(rows, period=period, anchor_date=anchor)
    narrative = financial_report_service.narrative(summary, llm_client)
    return jsonify({"success": True, "summary": summary, "report": narrative})



@app.post("/api/v1/invoices/voucher_excel")
def generate_voucher_excel() -> Any:
    """根据选中的发票列表生成 Excel 格式的记账凭证并返回文件。请求体: { invoice_ids: [id1, id2, ...] }"""
    data = request.get_json(force=True)
    invoice_ids = data.get("invoice_ids") or []
    if not invoice_ids or not isinstance(invoice_ids, list):
        return jsonify({"success": False, "error": "invoice_ids required"}), 400

    try:
        rows = []

        with db_session() as session:
            docs = session.query(Document).filter(Document.id.in_(invoice_ids)).all()
            for doc in docs:
                summary = doc.vendor or doc.file_name or ''
                # 为每个 ledger entry 生成借/贷行
                for le in doc.ledger_entries:
                    amt = float(le.amount or 0.0)
                    # 借方行
                    rows.append({"summary": summary, "account": le.debit_account or '', "debit": amt, "credit": None})
                    # 贷方行
                    rows.append({"summary": '', "account": le.credit_account or '', "debit": None, "credit": amt})

        # helper: convert amount to digit cells (string per cell), width 12
        def amount_to_cells(amount):
            if amount is None:
                return [""] * 12
            # amount as cents integer
            amt = Decimal(str(amount))
            cents = int((amt * 100).to_integral_value())
            s = str(abs(cents)).rjust(12, '0')  # pad to 12
            return list(s)

        # try to load template if exists
        template_paths = [
            DATA_DIR / 'templates' / 'voucher_template.xlsx',
            Path('voucher_template.xlsx'),
        ]
        wb = None
        ws = None
        for p in template_paths:
            try:
                if p.exists():
                    wb = load_workbook(p)
                    ws = wb.active
                    break
            except Exception:
                wb = None
                ws = None
        if wb is None:
            wb = Workbook()
            ws = wb.active

        start_row = 8
        for i, r in enumerate(rows):
            row = start_row + i
            ws.cell(row=row, column=1, value=r.get('summary', ''))  # A
            ws.cell(row=row, column=3, value=r.get('account', ''))  # C
            debit_cells = amount_to_cells(r.get('debit'))
            for k, v in enumerate(debit_cells):
                ws.cell(row=row, column=6 + k, value=v)  # F+
            credit_cells = amount_to_cells(r.get('credit'))
            for k, v in enumerate(credit_cells):
                ws.cell(row=row, column=18 + k, value=v)  # R+

        out_dir = DATA_DIR / 'output' / 'vouchers'
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = out_dir / f"vouchers_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx"
        wb.save(filename)

        return send_file(str(filename), as_attachment=True, download_name=filename.name)
    except Exception as e:
        logging.exception("Failed to generate voucher excel")
        return jsonify({"success": False, "error": str(e)}), 500


@app.post("/api/v1/analytics/query")
def run_analytics() -> Any:
    data = request.get_json(force=True)
    request_model = AnalyticsQueryRequest(**data)
    insight = services["analytics"].query(request_model)
    return jsonify(insight.model_dump())


@app.post("/api/v1/auth/login")
def api_login() -> Any:
    data = request.get_json(force=True)
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"success": False, "error": "邮箱和密码必填"}), 400
    user = authenticate(email=email, password=password)
    if not user:
        return jsonify({"success": False, "error": "账号或密码错误"}), 401
    session["user_id"] = user.id
    return jsonify({"success": True, "user": {"id": user.id, "name": user.name, "email": user.email}})


@app.post("/api/v1/auth/register")
def api_register() -> Any:
    data = request.get_json(force=True)
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    if not all([name, email, password]):
        return jsonify({"success": False, "error": "姓名/邮箱/密码不能为空"}), 400
    user = create_user(name=name, email=email, password=password)
    return jsonify({"success": True, "user": {"id": user.id, "name": user.name, "email": user.email}})


@app.post("/api/v1/auth/logout")
def api_logout() -> Any:
    session.pop("user_id", None)
    return jsonify({"success": True})


@app.get("/api/v1/auth/me")
def api_me() -> Any:
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False})
    user = get_user(user_id)
    if not user:
        session.pop("user_id", None)
        return jsonify({"success": False})
    return jsonify({"success": True, "user": {"id": user.id, "name": user.name, "email": user.email}})


@app.get("/api/v1/users")
def list_all_users() -> Any:
    return jsonify({"success": True, "users": list_users()})


@app.get("/api/v1/dashboard/summary")
def dashboard_summary_api() -> Any:
    days = int(request.args.get("days", 14))
    user_id = request.args.get("user_id") or session.get("user_id")
    data = dashboard_summary(days=days, user_id=user_id)
    return jsonify({"success": True, "data": data})


@app.post("/api/v1/feedback")
def collect_feedback() -> Any:
    data = request.get_json(force=True)
    request_model = FeedbackRequest(**data)
    services["feedback"].record(request_model)
    audit_logger.log("feedback", {"count": len(request_model.corrections)})
    return jsonify({"success": True})


@app.post("/api/v1/policies")
def upload_policy() -> Any:
    data = request.get_json(force=True)
    policy = PolicyDocument(**data)
    vector_store.add_texts([policy.content], [policy.model_dump()])
    return jsonify({"success": True})


@app.post("/api/v1/assistant/query")
def assistant_query() -> Any:
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    days = int(data.get("days", 120))
    user_id = data.get("user_id") or session.get("user_id")
    if not question:
        return jsonify({"success": False, "error": "question 不能为空"}), 400
    result = assistant_service.query(question=question, user_id=user_id, days=days)
    return jsonify({"success": True, **result})


@app.errorhandler(Exception)
def handle_exception(error: Exception):  # type: ignore[override]
    logging.exception("API Error")
    return jsonify({"success": False, "error": str(error)}), 500


def _parse_form_json(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


if __name__ == "__main__":
    import os

    port = int(os.getenv("PORT", "9000"))
    app.run(host="0.0.0.0", port=port, debug=settings.debug)
