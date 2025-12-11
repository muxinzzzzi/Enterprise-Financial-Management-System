"""自然语言分析与查询模块。"""
from __future__ import annotations

import json
import re
import time
from collections import OrderedDict
from typing import Dict, List, Sequence

from llm_client import LLMClient
from models.schemas import AnalyticsInsight, AnalyticsQueryRequest, AnalyticsRecord, DocumentResult
from utils.file_ops import read_analytics_cache, write_analytics_cache
from utils.prompts import NL_QUERY_PROMPT


class AnalyticsService:
    """自然语言分析与查询模块，提供缓存、语义筛选与稳健的 LLM 调用。"""

    DEFAULT_CACHE_LIMIT = 5000
    LLM_MAX_TOKENS = 2048
    LLM_MIN_TOKENS = 256
    LLM_RETRIES = 2

    def __init__(self, llm_client: LLMClient, cache_limit: int | None = None) -> None:
        self.llm = llm_client
        self.cache_limit = cache_limit or self.DEFAULT_CACHE_LIMIT
        self.records: "OrderedDict[str, AnalyticsRecord]" = OrderedDict()
        self._load_cache()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def sync(self, documents: List[DocumentResult]) -> None:
        """增量同步最新票据结果，确保幂等并限制缓存大小。"""
        changed = False
        for doc in documents:
            record = AnalyticsRecord.from_document(doc)
            if not record.document_id:
                continue
            if self._upsert_record(record):
                changed = True
        if changed:
            self._persist_cache()

    def query(self, request: AnalyticsQueryRequest) -> AnalyticsInsight:
        """对外查询接口，包含语义裁剪 + JSON 修复 + 错误兜底。"""
        context_records = self._select_context(request.question, request.context_limit)
        if not context_records:
            return AnalyticsInsight(question=request.question, answer="暂无可用的历史数据用于分析", generated_sql=None)

        prompt_payload = json.dumps([record.prompt_payload() for record in context_records], ensure_ascii=False)
        prompt = NL_QUERY_PROMPT.format(records=prompt_payload, question=request.question)
        messages = [
            {"role": "system", "content": "你是一名资深的企业财务分析助理，必须确保输出遵守 JSON 格式。"},
            {"role": "user", "content": prompt},
        ]

        try:
            reply = self._call_llm(messages, desired_records=len(context_records))
        except RuntimeError as exc:
            return AnalyticsInsight(question=request.question, answer=f"LLM 调用失败：{exc}", generated_sql=None)

        data = self._parse_llm_response(reply)
        answer = data.get("answer") or reply
        sql = data.get("sql")
        return AnalyticsInsight(question=request.question, answer=answer, generated_sql=sql)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _load_cache(self) -> None:
        """读取 JSON 缓存并恢复为结构化记录。"""
        raw_records = read_analytics_cache()
        for payload in raw_records:
            try:
                record = AnalyticsRecord(**payload)
            except Exception:
                continue
            self.records[record.document_id] = record
        self._trim_cache()

    def _persist_cache(self) -> None:
        serialized = [record.model_dump(mode="json") for record in self.records.values()]
        write_analytics_cache(serialized)

    def _upsert_record(self, record: AnalyticsRecord) -> bool:
        existing = self.records.get(record.document_id)
        if existing:
            existing_signature = existing.model_dump(exclude={"created_at"})
            new_signature = record.model_dump(exclude={"created_at"})
            if existing_signature == new_signature:
                return False
            self.records.pop(record.document_id)
        self.records[record.document_id] = record
        self._trim_cache()
        return True

    def _trim_cache(self) -> None:
        while len(self.records) > self.cache_limit:
            self.records.popitem(last=False)

    def _select_context(self, question: str, limit: int) -> List[AnalyticsRecord]:
        """简单的关键词打分 + 最近优先策略，减少无关上下文。"""
        if not self.records:
            return []

        tokens = {token for token in re.split(r"\W+", question.lower()) if len(token) >= 2}
        ranked: List[tuple[int, float, AnalyticsRecord]] = []
        for record in self.records.values():
            haystack = f"{record.vendor or ''} {record.category or ''} {record.currency}".lower()
            score = sum(1 for token in tokens if token and token in haystack)
            timestamp = record.created_at.timestamp() if record.created_at else 0.0
            ranked.append((score, timestamp, record))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)

        selected: List[AnalyticsRecord] = []
        selected_ids = set()
        for score, _, record in ranked:
            if score <= 0:
                continue
            if record.document_id in selected_ids:
                continue
            selected.append(record)
            selected_ids.add(record.document_id)
            if len(selected) >= limit:
                break

        if len(selected) < limit:
            for record in reversed(list(self.records.values())):
                if record.document_id in selected_ids:
                    continue
                selected.append(record)
                selected_ids.add(record.document_id)
                if len(selected) >= limit:
                    break
        return selected

    def _call_llm(self, messages: Sequence[Dict[str, str]], desired_records: int) -> str:
        """带重试的 LLM 调用，动态分配 max_tokens。"""
        token_budget = min(
            self.LLM_MAX_TOKENS,
            max(self.LLM_MIN_TOKENS, 256 + desired_records * 32),
        )
        last_error: Exception | None = None
        for attempt in range(self.LLM_RETRIES):
            try:
                return self.llm.chat(list(messages), max_tokens=token_budget)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(str(last_error)) from last_error

    def _parse_llm_response(self, reply: str) -> Dict[str, str]:
        """解析 LLM 输出，必要时裁剪或尝试修复 JSON。"""
        parsers = [
            lambda text: json.loads(text),
            lambda text: json.loads(self._extract_json_block(text)),
        ]
        for parser in parsers:
            try:
                parsed = parser(reply)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        return {"answer": reply[:1000], "sql": None}

    @staticmethod
    def _extract_json_block(text: str) -> str:
        """提取首个 {} 包裹的 JSON 片段，常用于修复多余解释。"""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return text
        return text[start : end + 1]


__all__ = ["AnalyticsService"]
