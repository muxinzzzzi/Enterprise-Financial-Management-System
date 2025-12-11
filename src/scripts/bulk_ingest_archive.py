"""批量导入 archive 目录下的票据到系统中。"""
from __future__ import annotations

import base64
from pathlib import Path

from app import journal_service, pipeline  # type: ignore
from config import ROOT_DIR
from models.schemas import DocumentPayload, PipelineOptions, ReconciliationRequest
from services.accounting.persistence_service import persist_results
from services.user_service import create_user

ARCHIVE_DIR = ROOT_DIR.parent / "archive"
TARGET_EMAIL = "user1@example.com"
TARGET_NAME = "user1"
DEFAULT_PASSWORD = "123456"


def iter_invoice_files(directory: Path):
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".pdf"}:
            yield path


def main() -> None:
    if not ARCHIVE_DIR.exists():
        raise SystemExit(f"未找到数据集目录: {ARCHIVE_DIR}")

    user = create_user(TARGET_NAME, TARGET_EMAIL, DEFAULT_PASSWORD)
    print(f"✅ 用户 {user.name} ({user.email}) 已就绪")

    files = list(iter_invoice_files(ARCHIVE_DIR))
    if not files:
        raise SystemExit("未在 archive 中发现票据文件")

    print(f"📂 准备导入 {len(files)} 份票据")
    for idx, file_path in enumerate(files, start=1):
        with open(file_path, "rb") as fp:
            content_base64 = base64.b64encode(fp.read()).decode("utf-8")

        payload = DocumentPayload(
            file_name=file_path.name,
            file_content_base64=content_base64,
            meta={
                "user_email": TARGET_EMAIL,
                "user_name": TARGET_NAME,
                "source": "archive",
            },
        )

        request = ReconciliationRequest(documents=[payload], policies=[], options=PipelineOptions())
        result = pipeline.run(request)
        for doc in result.documents:
            doc.journal_entries = journal_service.generate(doc)
        persist_results(result.documents, request.documents)
        print(f"[{idx}/{len(files)}] 已导入 {file_path.name}")
        if idx >= 5:
            print("⚠️ 已导入前 5 个文件，提前结束")
            break

    print("🎉 数据集导入完成！")


if __name__ == "__main__":
    main()
