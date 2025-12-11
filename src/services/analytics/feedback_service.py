"""人机共审与主动学习模块。"""
from __future__ import annotations

import json
import os
from collections import deque
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List

from config import FEEDBACK_FILE
from models.schemas import FeedbackItem, FeedbackRequest


class FeedbackService:
    """结构化反馈存储 + few-shot 构造 + 并发安全写入。"""

    SCHEMA_VERSION = 1

    def __init__(self, cache_limit: int = 300) -> None:
        self.cache_limit = cache_limit
        self._cache: Deque[Dict[str, Any]] = deque(maxlen=cache_limit)
        self._dedup_keys: set[str] = set()
        self._cache_mtime: float = 0.0
        self._load_cache()

    def record(
        self,
        request: FeedbackRequest,
        reviewer_id: str | None = None,
        default_importance: float = 0.6,
    ) -> None:
        """记录用户修正，带并发锁与去重。"""
        self._refresh_cache_if_needed()
        for item in request.corrections:
            entry = self._build_entry(item, reviewer_id, default_importance)
            dedup_key = self._dedup_key(entry)
            if dedup_key in self._dedup_keys:
                continue
            self._append_entry(entry)
            self._update_cache(entry, dedup_key)

    def few_shot_examples(self, limit: int = 5) -> List[str]:
        """返回结构化 JSON few-shot，保证字段多样性与重要度优先。"""
        self._refresh_cache_if_needed()
        pool = list(self._cache)
        if not pool:
            return []

        # 按重要度与时间排序
        pool.sort(
            key=lambda x: (
                -(x.get("importance") or 0.5),
                x.get("timestamp", ""),
            )
        )

        result: List[Dict[str, Any]] = []
        used_fields: set[str] = set()

        # 优先保证不同字段覆盖
        for entry in pool:
            field = entry.get("field_name")
            if field and field not in used_fields:
                result.append(entry)
                used_fields.add(field)
                if len(result) >= limit:
                    break

        # 不足时按近期/重要度补齐
        if len(result) < limit:
            for entry in pool:
                if entry in result:
                    continue
                result.append(entry)
                if len(result) >= limit:
                    break

        return [self._format_example(item) for item in result[:limit]]

    # ---------------- 内部方法 ----------------
    def _load_cache(self) -> None:
        if not FEEDBACK_FILE.exists():
            return
        entries = self._read_tail(self.cache_limit)
        self._cache.clear()
        for entry in entries:
            self._cache.append(entry)
            self._dedup_keys.add(self._dedup_key(entry))
        self._cache_mtime = FEEDBACK_FILE.stat().st_mtime

    def _refresh_cache_if_needed(self) -> None:
        if not FEEDBACK_FILE.exists():
            self._cache.clear()
            self._dedup_keys.clear()
            self._cache_mtime = 0.0
            return
        mtime = FEEDBACK_FILE.stat().st_mtime
        if mtime > self._cache_mtime:
            self._load_cache()

    def _append_entry(self, entry: Dict[str, Any]) -> None:
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_file(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, "a", encoding="utf-8") as fp:
                fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._cache_mtime = FEEDBACK_FILE.stat().st_mtime

    def _update_cache(self, entry: Dict[str, Any], dedup_key: str) -> None:
        self._cache.append(entry)
        self._dedup_keys.add(dedup_key)

    def _build_entry(
        self,
        item: FeedbackItem,
        reviewer_id: str | None,
        default_importance: float,
    ) -> Dict[str, Any]:
        importance = item.importance if item.importance is not None else default_importance
        revision = item.revision or self._next_revision(item.document_id, item.field_name)
        return {
            "schema_version": self.SCHEMA_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "document_id": item.document_id,
            "field_name": item.field_name,
            "old_value": item.old_value,
            "new_value": item.new_value,
            "comment": item.comment,
            "reviewer_id": item.reviewer_id or reviewer_id,
            "importance": round(float(importance), 3),
            "confidence": item.confidence,
            "revision": revision,
        }

    def _next_revision(self, document_id: str, field_name: str) -> int:
        rev = 0
        for entry in reversed(self._cache):
            if entry.get("document_id") == document_id and entry.get("field_name") == field_name:
                try:
                    rev = int(entry.get("revision") or 0)
                except (TypeError, ValueError):
                    rev = 0
                break
        return rev + 1

    def _format_example(self, entry: Dict[str, Any]) -> str:
        def clip(val: Any, limit: int = 200) -> Any:
            if val is None:
                return val
            text = str(val)
            return text if len(text) <= limit else text[:limit] + "...(truncated)"

        payload = {
            "field_name": entry.get("field_name"),
            "old": clip(entry.get("old_value")),
            "new": clip(entry.get("new_value")),
            "reason": clip(entry.get("comment"), 120),
            "importance": entry.get("importance", 0.5),
            "revision": entry.get("revision"),
            "reviewer_id": entry.get("reviewer_id"),
        }
        return json.dumps(payload, ensure_ascii=False)

    def _dedup_key(self, entry: Dict[str, Any]) -> str:
        return f"{entry.get('document_id')}::{entry.get('field_name')}::{entry.get('new_value')}"

    def _read_tail(self, limit: int) -> List[Dict[str, Any]]:
        if not FEEDBACK_FILE.exists():
            return []
        dq: Deque[Dict[str, Any]] = deque(maxlen=limit)
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    dq.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return list(dq)

    @contextmanager
    def _lock_file(self, path: Path):
        lock_path = Path(f"{path}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        try:
            try:
                import fcntl

                fcntl.flock(lock_fd, fcntl.LOCK_EX)
            except ImportError:
                pass
            yield
        finally:
            try:
                import fcntl

                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except ImportError:
                pass
            os.close(lock_fd)


__all__ = ["FeedbackService"]
