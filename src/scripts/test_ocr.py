"""简单脚本：读取一张图片，走 ingestion + OCR 流程并打印结果。"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import get_settings
from models.schemas import DocumentPayload
from services.ingestion.ingestion_service import DocumentIngestionService
from services.ingestion.ocr_service import MultiEngineOCRService


def run(image_path: Path) -> None:
    if not image_path.exists():
        raise FileNotFoundError(f"找不到文件: {image_path}")

    settings = get_settings()
    print("---- 配置检查 ----")
    print(f"OCR_ENDPOINTS: {settings.ocr_endpoints}")
    print(f"Baidu OCR: {'已配置' if settings.baidu_app_id and settings.baidu_api_key and settings.baidu_secret_key else '未配置'}")

    content_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    payload = DocumentPayload(file_name=image_path.name, file_content_base64=content_b64, meta={"document_id": "doc_test"})

    ingestion = DocumentIngestionService()
    ocr = MultiEngineOCRService()

    print("---- 开始 ingestion ----")
    ingested = ingestion.ingest(payload)
    if ingested.get("error"):
        raise RuntimeError(f"ingestion 失败: {ingested['error']}")

    print("---- 开始 OCR ----")
    ocr_result = ocr.recognize(ingested)

    print("---- 结果 ----")
    engine = ocr_result.get("spans")[0].engine if ocr_result.get("spans") else "N/A"
    print(f"engine: {engine}")
    print(f"confidence: {ocr_result.get('confidence')}")
    text = ocr_result.get("text", "")
    preview = text[:400].replace("\n", "\\n")
    print(f"text preview (前400字符): {preview}")
    if ocr_result.get("errors"):
        print("errors:", ocr_result.get("errors"))
    fields = ocr_result.get("fields") if isinstance(ocr_result.get("fields"), dict) else {}
    invoice_type = fields.get("invoice_type")
    if invoice_type:
        print(f"invoice_type: {invoice_type}")
    structured = fields.get("structured")
    if structured:
        print("structured fields (截断4000):")
        print(json.dumps(structured, ensure_ascii=False)[:4000])
    spans = ocr_result.get("spans") or []
    if spans:
        print(f"span count: {len(spans)}, first span preview: {spans[0].text[:200]}")
    raw = {k: v for k, v in ocr_result.items() if k != "spans"}
    print("raw JSON (截断6000):")
    print(json.dumps(raw, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试 OCR 调用")
    parser.add_argument(
        "--image",
        type=Path,
        default=Path("/Users/muxin/Desktop/对账系统/InvoiceDatasets-master/dataset/images/taxi_test/taxi_0127.jpg"),
        help="要测试的图片路径",
    )
    args = parser.parse_args()
    run(args.image)

