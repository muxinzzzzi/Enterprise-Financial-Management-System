"""基于RAG的政策校验模块，最小侵入增强版。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from config import get_settings
from llm_client import LLMClient
from models.schemas import PolicyDocument, PolicyFlag
from repositories.vector_store import VectorStore

from .rag_retriever import RAGRetriever
from .rule_summarizer import RuleSummarizer
from .two_stage_llm import TwoStageLLM


@dataclass
class PolicyValidationDebugResult:
    flags: List[PolicyFlag]
    context: str
    hits: List[Dict[str, Any]]
    reasoning: str


class PolicyValidationService:
    def __init__(self, vector_store: VectorStore, llm_client: LLMClient) -> None:
        self.settings = get_settings()
        self.store = vector_store
        self.llm = llm_client
        self.summarizer = RuleSummarizer(llm_client)
        self.retriever = RAGRetriever(
            vector_store,
            llm=llm_client,
            enable_query_rewrite=getattr(self.settings, "enable_policy_query_rewrite", False),
        )
        self.two_stage = TwoStageLLM(llm_client)
        self.shadow_path = Path(__file__).with_name("shadow_rules.json")

    def _load_shadow_rules(self) -> Tuple[List[str], List[dict]]:
        if not self.shadow_path.exists():
            return [], []
        try:
            data = json.loads(self.shadow_path.read_text(encoding="utf-8"))
        except Exception:
            return [], []
        texts: List[str] = []
        metas: List[dict] = []
        for item in data if isinstance(data, list) else []:
            summary = item.get("summary") or item.get("content") or ""
            content = item.get("content") or summary
            tags = {
                "expense_type": item.get("expense_type") or "",
                "scene": item.get("scene") or "",
                "city_level": item.get("city_level") or "",
            }
            texts.append(summary)
            metas.append(
                {
                    "title": item.get("title", "shadow_rule"),
                    "summary": summary,
                    "content": content,
                    "source": "shadow_rule",
                    **{k: v for k, v in tags.items() if v},
                }
            )
        return texts, metas

    def ingest_policies(self, policies: List[PolicyDocument]) -> None:
        if not policies:
            return
        summaries, metas = self.summarizer.summarize_batch(policies)
        shadow_texts, shadow_metas = self._load_shadow_rules()

        all_texts = summaries + shadow_texts
        all_metas = metas + shadow_metas

        self.store.clear()
        self.store.add_texts(all_texts, all_metas)

    def _to_flags(self, flags_raw: List[Dict[str, Any]]) -> List[PolicyFlag]:
        try:
            return [PolicyFlag(**flag) for flag in flags_raw[:10]]
        except Exception:
            return []

    def validate(self, document_payload: Dict[str, Any]) -> List[PolicyFlag]:
        if not self.settings.enable_policy_rag or not self.store.records:
            return []

        context_text, _hits = self.retriever.retrieve(document_payload)
        if not context_text:
            return []

        flags_raw, _ = self.two_stage.generate_flags_with_reasoning(context_text, document_payload)
        return self._to_flags(flags_raw)

    def validate_with_debug(self, document_payload: Dict[str, Any]) -> PolicyValidationDebugResult:
        if not self.settings.enable_policy_rag or not self.store.records:
            return PolicyValidationDebugResult([], "", [], "")

        context_text, hits = self.retriever.retrieve(document_payload)
        if not context_text:
            return PolicyValidationDebugResult([], "", hits, "")

        flags_raw, reasoning = self.two_stage.generate_flags_with_reasoning(context_text, document_payload)
        flags = self._to_flags(flags_raw)
        return PolicyValidationDebugResult(flags, context_text, hits, reasoning)


__all__ = ["PolicyValidationService", "PolicyValidationDebugResult"]
