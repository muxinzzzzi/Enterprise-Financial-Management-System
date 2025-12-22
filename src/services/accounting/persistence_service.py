"""将对账结果写入 SQLite。"""
from __future__ import annotations

from pathlib import Path
from typing import List
from datetime import datetime
import logging
import re

from PIL import Image, ImageDraw, ImageFont

from werkzeug.security import generate_password_hash

from database import db_session
from models.db_models import Document, User
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
                status="uploaded",
                raw_result=raw,
            )
            session.merge(doc_record)


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
    """使用 Pillow 生成易读的中文会计凭证 PDF（表格+签字栏）。"""
    try:
        out_dir = DATA_DIR / "output" / "vouchers"
        out_dir.mkdir(parents=True, exist_ok=True)
        page_width, page_height = 1240, 1754  # A4 约 150-200dpi
        page = Image.new("RGB", (page_width, page_height), "white")
        draw = ImageDraw.Draw(page)

        def _try_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
            candidates = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
            for p in candidates:
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        font = _try_font(20)
        font_small = _try_font(16)
        font_title = _try_font(30)

        def _text_size(text: str, f) -> tuple[int, int]:
            """兼容 Pillow 新旧版本的文字测量。"""
            try:
                bbox = draw.textbbox((0, 0), text, font=f)
                return bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                try:
                    return draw.textsize(text, font=f)
                except Exception:
                    return len(text) * 10, 16

        margin = 80
        line_h = 34
        text_color = (34, 45, 60)
        grid_color = (180, 180, 180)

        def text_line(x: int, y: int, text: str, f=font) -> int:
            draw.text((x, y), text, fill=text_color, font=f)
            return y + line_h

        # 基本信息
        title = "记账凭证"
        tw, th = _text_size(title, font_title)
        draw.text(((page_width - tw) / 2, margin), title, fill=text_color, font=font_title)
        y = margin + th + 10

        issue_date = (
            doc.issue_date
            or doc.normalized_fields.get("issue_date")
            or doc.structured_fields.get("issue_date")
            or datetime.utcnow().strftime("%Y-%m-%d")
        )
        voucher_no = doc.document_id.split("_")[-1]
        y = text_line(margin, y, f"凭证日期：{issue_date}")
        y = text_line(margin, y, f"凭证字号：记字第 {voucher_no} 号")
        y = text_line(margin, y, f"附单据：1 张")

        y += line_h // 2
        draw.line((margin, y, page_width - margin, y), fill=grid_color, width=2)
        y += line_h // 2

        # 表头
        col_summary_w = 360
        col_account_w = 340
        col_amount_w = 180
        x_summary = margin
        x_account = x_summary + col_summary_w
        x_debit = x_account + col_account_w
        x_credit = x_debit + col_amount_w
        header_y = y

        def draw_header_cell(x0: int, x1: int, text: str) -> None:
            draw.text((x0 + 8, header_y), text, fill=text_color, font=font)
            draw.line((x0, header_y + line_h, x1, header_y + line_h), fill=grid_color, width=2)

        draw_header_cell(x_summary, x_account, "摘要")
        draw_header_cell(x_account, x_debit, "会计科目")
        draw_header_cell(x_debit, x_credit, "借方金额(元)")
        draw_header_cell(x_credit, x_credit + col_amount_w, "贷方金额(元)")
        y = header_y + line_h + 4

        # 准备分录行（保证有借贷两行）
        rows: list[dict] = []
        for entry in entries:
            memo = entry.get("memo") or doc.vendor or doc.file_name
            amt = float(entry.get("amount", 0) or 0)
            debit_acc = entry.get("debit_account") or ""
            credit_acc = entry.get("credit_account") or ""
            rows.append({"summary": memo, "account": debit_acc, "debit": amt, "credit": 0.0})
            rows.append({"summary": memo, "account": credit_acc, "debit": 0.0, "credit": amt})

        if not rows:
            rows.append(
                {
                    "summary": doc.vendor or doc.file_name,
                    "account": "管理费用-其他",
                    "debit": float(doc.total_amount or 0.0),
                    "credit": 0.0,
                }
            )
            rows.append(
                {
                    "summary": doc.vendor or doc.file_name,
                    "account": "银行存款",
                    "debit": 0.0,
                    "credit": float(doc.total_amount or 0.0),
                }
            )

        total_debit = 0.0
        total_credit = 0.0

        def fmt_amt(v: float | None) -> str:
            if v is None:
                return ""
            return f"{v:,.2f}"

        for row in rows:
            y = text_line(x_summary, y, str(row.get("summary", "")), f=font_small)
            text_line(x_account, y - line_h, str(row.get("account", "")), f=font_small)
            debit = row.get("debit")
            credit = row.get("credit")
            if debit:
                total_debit += float(debit)
            if credit:
                total_credit += float(credit)
            text_line(x_debit, y - line_h, fmt_amt(debit), f=font_small)
            text_line(x_credit, y - line_h, fmt_amt(credit), f=font_small)
            draw.line((margin, y, page_width - margin, y), fill=grid_color, width=1)
            y += 6

        # 合计
        y += 4
        draw.line((margin, y, page_width - margin, y), fill=grid_color, width=2)
        y = text_line(x_summary, y + 6, "合计", f=font)
        text_line(x_debit, y - line_h, fmt_amt(total_debit), f=font)
        text_line(x_credit, y - line_h, fmt_amt(total_credit), f=font)
        y += 6
        draw.line((margin, y, page_width - margin, y), fill=grid_color, width=2)
        y += line_h

        # 提示与签字
        note = (
            "提示：请根据本单位会计科目需要，调整“管理费用—差旅费/交通费”等科目；"
            "若通过银行/公务卡支付，可将“库存现金”改为“银行存款”。"
        )
        y = text_line(margin, y, note, f=font_small)
        y += line_h
        sign_y = y
        sign_labels = ["制单", "审核", "出纳", "记账"]
        for idx, label in enumerate(sign_labels):
            x = margin + idx * 220
            draw.text((x, sign_y), f"{label}：__________", fill=text_color, font=font)

        file_path = out_dir / f"{doc.document_id}.pdf"
        page.save(file_path, "PDF", resolution=150.0)
        return file_path
    except Exception:
        logging.exception("generate voucher pdf failed")
        return None


def next_voucher_no() -> int:
    """根据输出目录现有凭证文件，生成下一个流水号（从1开始）。"""
    out_dir = DATA_DIR / "output" / "vouchers"
    out_dir.mkdir(parents=True, exist_ok=True)
    max_no = 0
    pattern = re.compile(r"voucher_(\d+)\.pdf$")
    for p in out_dir.glob("voucher_*.pdf"):
        m = pattern.search(p.name)
        if m:
            try:
                max_no = max(max_no, int(m.group(1)))
            except Exception:
                continue
    return max_no + 1


def generate_combined_voucher(documents: List[DocumentResult], entries: List[dict]) -> tuple[Path | None, int, str]:
    """
    根据多张发票合成一个凭证 PDF。
    返回 (path, voucher_no, voucher_date)
    """
    if not documents:
        return None, 0, ""
    voucher_no = next_voucher_no()
    voucher_date = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        out_dir = DATA_DIR / "output" / "vouchers"
        out_dir.mkdir(parents=True, exist_ok=True)
        page_width, page_height = 1240, 1754  # A4
        page = Image.new("RGB", (page_width, page_height), "white")
        draw = ImageDraw.Draw(page)

        def _try_font(size: int):
            candidates = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
            for p in candidates:
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        font = _try_font(20)
        font_small = _try_font(16)
        font_title = _try_font(30)

        def _text_size(text: str, f):
            try:
                bbox = draw.textbbox((0, 0), text, font=f)
                return bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                try:
                    return draw.textsize(text, font=f)
                except Exception:
                    return len(text) * 10, 16

        margin = 80
        line_h = 34
        text_color = (34, 45, 60)
        grid_color = (180, 180, 180)

        def text_line(x: int, y: int, text: str, f=font) -> int:
            draw.text((x, y), text, fill=text_color, font=f)
            return y + line_h

        title = "记账凭证（合并）"
        tw, th = _text_size(title, font_title)
        draw.text(((page_width - tw) / 2, margin), title, fill=text_color, font=font_title)
        y = margin + th + 10

        y = text_line(margin, y, f"凭证日期：{voucher_date}")
        y = text_line(margin, y, f"凭证字号：记字第 {voucher_no} 号")
        y = text_line(margin, y, f"包含发票：{len(documents)} 张")

        y += line_h // 2
        draw.line((margin, y, page_width - margin, y), fill=grid_color, width=2)
        y += line_h // 2

        col_summary_w = 360
        col_account_w = 340
        col_amount_w = 180
        x_summary = margin
        x_account = x_summary + col_summary_w
        x_debit = x_account + col_account_w
        x_credit = x_debit + col_amount_w
        header_y = y

        def draw_header_cell(x0: int, x1: int, text: str) -> None:
            draw.text((x0 + 8, header_y), text, fill=text_color, font=font)
            draw.line((x0, header_y + line_h, x1, header_y + line_h), fill=grid_color, width=2)

        draw_header_cell(x_summary, x_account, "摘要")
        draw_header_cell(x_account, x_debit, "会计科目")
        draw_header_cell(x_debit, x_credit, "借方金额(元)")
        draw_header_cell(x_credit, x_credit + col_amount_w, "贷方金额(元)")
        y = header_y + line_h + 4

        rows: list[dict] = []
        for entry in entries:
            memo = entry.get("memo") or ""
            amt = float(entry.get("amount", 0) or 0)
            debit_acc = entry.get("debit_account") or ""
            credit_acc = entry.get("credit_account") or ""
            rows.append({"summary": memo, "account": debit_acc, "debit": amt, "credit": 0.0})
            rows.append({"summary": memo, "account": credit_acc, "debit": 0.0, "credit": amt})

        if not rows:
            rows.append({"summary": "无分录", "account": "", "debit": 0.0, "credit": 0.0})

        total_debit = 0.0
        total_credit = 0.0

        def fmt_amt(v: float | None) -> str:
            if v is None:
                return ""
            return f"{v:,.2f}"

        for row in rows:
            y = text_line(x_summary, y, str(row.get("summary", "")), f=font_small)
            text_line(x_account, y - line_h, str(row.get("account", "")), f=font_small)
            debit = row.get("debit")
            credit = row.get("credit")
            if debit:
                total_debit += float(debit)
            if credit:
                total_credit += float(credit)
            text_line(x_debit, y - line_h, fmt_amt(debit), f=font_small)
            text_line(x_credit, y - line_h, fmt_amt(credit), f=font_small)
            draw.line((margin, y, page_width - margin, y), fill=grid_color, width=1)
            y += 6

        y += 4
        draw.line((margin, y, page_width - margin, y), fill=grid_color, width=2)
        y = text_line(x_summary, y + 6, "合计", f=font)
        text_line(x_debit, y - line_h, fmt_amt(total_debit), f=font)
        text_line(x_credit, y - line_h, fmt_amt(total_credit), f=font)
        y += 6
        draw.line((margin, y, page_width - margin, y), fill=grid_color, width=2)
        y += line_h

        note = "提示：本凭证由多张发票合并生成，可按需调整科目与金额。"
        y = text_line(margin, y, note, f=font_small)
        y += line_h
        sign_y = y
        sign_labels = ["制单", "审核", "出纳", "记账"]
        for idx, label in enumerate(sign_labels):
            x = margin + idx * 220
            draw.text((x, sign_y), f"{label}：__________", fill=text_color, font=font)

        file_path = out_dir / f"voucher_{voucher_no}.pdf"
        page.save(file_path, "PDF", resolution=150.0)
        return file_path, voucher_no, voucher_date
    except Exception:
        logging.exception("generate combined voucher failed")
        return None, voucher_no, voucher_date


__all__ = ["persist_results", "generate_combined_voucher", "next_voucher_no"]
