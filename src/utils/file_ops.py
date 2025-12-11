"""通用文件与文本工具。"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Iterable, List

from config import ANALYTICS_CACHE, DATA_DIR, FEEDBACK_FILE


def save_base64_file(file_name: str, content_base64: str, sub_dir: str = "input") -> Path:
    target_dir = DATA_DIR / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / file_name
    with open(file_path, "wb") as fp:
        fp.write(base64.b64decode(content_base64))
    return file_path


def read_text_files(paths: Iterable[Path]) -> List[str]:
    texts = []
    for path in paths:
        if path.exists() and path.is_file():
            texts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return texts


def append_json_line(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_feedback() -> List[dict]:
    if not FEEDBACK_FILE.exists():
        return []
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as fp:
        return [json.loads(line) for line in fp if line.strip()]


def read_analytics_cache() -> List[dict]:
    if not ANALYTICS_CACHE.exists():
        return []
    with open(ANALYTICS_CACHE, "r", encoding="utf-8") as fp:
        return json.load(fp)


def write_analytics_cache(payload: List[dict]) -> None:
    ANALYTICS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(ANALYTICS_CACHE, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)


def touch_policy_document(title: str, content: str) -> Path:
    sanitized = "".join(ch if ch.isalnum() else "_" for ch in title)[:80]
    file_path = DATA_DIR / "policy" / f"{sanitized}.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


__all__ = [
    "append_json_line",
    "read_analytics_cache",
    "read_feedback",
    "read_text_files",
    "save_base64_file",
    "touch_policy_document",
    "write_analytics_cache",
]
