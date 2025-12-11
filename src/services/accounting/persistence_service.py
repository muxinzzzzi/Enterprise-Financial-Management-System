"""将对账结果写入 SQLite。"""
from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

from werkzeug.security import generate_password_hash

from database import db_session
from models.db_models import Document, LedgerEntry, User
from models.schemas import DocumentPayload, DocumentResult, generate_id
from config import DATA_DIR

CATEGORY_TO_ACCOUNT = {
    "差旅": "管理费用-差旅费",
    "设备": "固定资产",
    "办公": "管理费用-办公费",
    "会议": "管理费用-会议费",
    "招待": "管理费用-业务招待费",
    "科研耗材": "研发支出-材料费",
    "其他": "管理费用-其他",
}


def persist_results(documents: List[DocumentResult], payloads: List[DocumentPayload]) -> None:
    if not documents:
        return
    with db_session() as session:
        for doc_result, payload in zip(documents, payloads):
            user = _resolve_user(session, payload)
            raw = doc_result.model_dump()
            doc_record = Document(
                id=doc_result.document_id,
                user_id=user.id,
                file_name=doc_result.file_name,
                file_path=payload.meta.get("file_path"),
                vendor=doc_result.vendor,
                amount=doc_result.total_amount,
                tax_amount=doc_result.tax_amount,
                currency=doc_result.currency,
                category=doc_result.category,
                status="auto_recorded",
                raw_result=raw,
            )

            entries = doc_result.journal_entries or [
                {
                    "debit_account": _map_debit_account(doc_result.category),
                    "credit_account": "现金",
                    "amount": float(doc_result.total_amount or 0.0),
                    "memo": f"AI自动记账：{doc_result.vendor or doc_result.file_name}",
                }
            ]
            voucher_path = _generate_voucher_pdf(doc_result, entries)
            raw["voucher_pdf_path"] = str(voucher_path) if voucher_path else None
            doc_record.raw_result = raw
            session.merge(doc_record)
            for entry_payload in entries:
                entry = LedgerEntry(
                    document_id=doc_result.document_id,
                    user_id=user.id,
                    debit_account=entry_payload.get("debit_account", _map_debit_account(doc_result.category)),
                    credit_account=entry_payload.get("credit_account", "现金"),
                    amount=float(entry_payload.get("amount", doc_result.total_amount or 0.0)),
                    memo=entry_payload.get("memo", doc_result.file_name),
                )
                session.add(entry)


def _resolve_user(session, payload: DocumentPayload) -> User:
    meta = payload.meta or {}
    email = meta.get("user_email") or "owner@example.com"
    name = meta.get("user_name") or email.split("@")[0]
    user = session.query(User).filter_by(email=email).first()
    if user:
        return user
    user = User(
        id=generate_id("usr"),
        name=name,
        email=email,
        role=meta.get("user_role", "owner"),
        password_hash=generate_password_hash(meta.get("default_password", "123456")),
    )
    session.add(user)
    session.flush()
    return user


def _map_debit_account(category: str | None) -> str:
    if not category:
        return CATEGORY_TO_ACCOUNT["其他"]
    return CATEGORY_TO_ACCOUNT.get(category, CATEGORY_TO_ACCOUNT["其他"])


def _generate_voucher_pdf(doc: DocumentResult, entries: List[dict]) -> Path | None:
    """使用 Pillow 生成简单凭证 PDF，避免新增重依赖。"""
    try:
        out_dir = DATA_DIR / "output" / "vouchers"
        out_dir.mkdir(parents=True, exist_ok=True)
        page = Image.new("RGB", (1240, 1754), "white")  # A4 300dpi 约
        draw = ImageDraw.Draw(page)
        try:
            font = ImageFont.truetype("arial.ttf", 18)
            title_font = ImageFont.truetype("arial.ttf", 26)
        except Exception:
            font = ImageFont.load_default()
            title_font = font

        y = 60
        draw.text((60, y), "会计凭证", fill=(34, 45, 60), font=title_font)
        y += 50
        draw.text((60, y), f"凭证号: {doc.document_id}", fill=(34, 45, 60), font=font)
        y += 28
        draw.text((60, y), f"供应商/抬头: {doc.vendor or '未知'}", fill=(34, 45, 60), font=font)
        y += 28
        draw.text((60, y), f"金额: {doc.total_amount or 0} {doc.currency}", fill=(34, 45, 60), font=font)
        y += 28
        draw.text((60, y), f"分类: {doc.category or '未分类'}", fill=(34, 45, 60), font=font)
        y += 40
        draw.text((60, y), "分录明细:", fill=(34, 45, 60), font=font)
        y += 28
        draw.line((60, y, 1180, y), fill=(200, 200, 200), width=2)
        y += 16
        for entry in entries:
            line = (
                f"借: {entry.get('debit_account','')} / 贷: {entry.get('credit_account','')} "
                f"金额: {entry.get('amount',0)} 备注: {entry.get('memo','')}"
            )
            draw.text((60, y), line, fill=(34, 45, 60), font=font)
            y += 26
            if y > 1600:
                break

        file_path = out_dir / f"{doc.document_id}.pdf"
        page.save(file_path, "PDF", resolution=150.0)
        return file_path
    except Exception:
        return None


__all__ = ["persist_results"]
