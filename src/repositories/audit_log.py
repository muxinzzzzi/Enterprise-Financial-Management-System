"""审计日志与可追溯信息管理。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from utils.file_ops import append_json_line


class AuditLogger:
    def __init__(self, path: Path):
        self.path = path

    def log(self, event: str, payload: Dict[str, Any]) -> None:
        append_json_line(
            self.path,
            {
                "timestamp": datetime.utcnow().isoformat(),
                "event": event,
                **payload,
            },
        )

    def replay(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        with open(self.path, "r", encoding="utf-8") as fp:
            return [json.loads(line) for line in fp if line.strip()]


__all__ = ["AuditLogger"]
