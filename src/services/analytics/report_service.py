"""审核报告生成模块。"""
from __future__ import annotations

import json
from typing import List

from llm_client import LLMClient
from models.schemas import DocumentResult
from utils.prompts import REPORT_PROMPT


class ReportService:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    def generate(self, documents: List[DocumentResult]) -> str:
        payload = json.dumps([doc.model_dump() for doc in documents], ensure_ascii=False)
        prompt = REPORT_PROMPT.format(payload=payload)
        try:
            return self.llm.chat([
                {"role": "system", "content": "你是财务审核总结机器人"},
                {"role": "user", "content": prompt},
            ], max_tokens=800)
        except Exception:
            return "\n".join([
                f"- {doc.file_name}: {len(doc.policy_flags)}条政策提醒, {len(doc.anomalies)}条异常"
                for doc in documents
            ])


__all__ = ["ReportService"]
