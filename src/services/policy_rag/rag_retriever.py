from __future__ import annotations

import json
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Dict, List, Optional, Sequence, Tuple

from llm_client import LLMClient
from repositories.vector_store import VectorStore


def _estimate_tokens(text: str) -> int:
    """粗略估算 tokens，避免上下文过长。"""
    return max(1, len(text) // 4)


@dataclass
class QuerySpec:
    text: str
    kind: str  # "payload_json" | "keywords" | "fallback" | "nl_query"


class RAGRetriever:
    """
    多路召回 + 去重 + 截断的检索器，带 query 权重、可选 NL 重写、证据编号。
    """

    WEIGHTS = {"payload_json": 1.2, "keywords": 1.0, "nl_query": 1.3, "fallback": 0.7}

    def __init__(
        self,
        store: VectorStore,
        llm: Optional[LLMClient] = None,
        top_ks: Sequence[int] = (5, 8, 12),
        max_items: int = 8,
        max_tokens: int = 1500,
        enable_query_rewrite: bool = False,
    ) -> None:
        self.store = store
        self.llm = llm
        self.top_ks = tuple(top_ks)
        self.max_items = max_items
        self.max_tokens = max_tokens
        self.enable_query_rewrite = enable_query_rewrite

    def _build_nl_query(self, payload: Dict[str, Any]) -> Optional[str]:
        if not self.enable_query_rewrite or not self.llm:
            return None
        prompt = dedent(
            f"""
            将以下报销 payload 总结为一句中文检索语句，便于匹配相关报销政策。
            只输出一句话，不要 JSON。
            payload: {json.dumps(payload, ensure_ascii=False)}
            """
        )
        try:
            return self.llm.chat(
                [
                    {"role": "system", "content": "你是检索语句生成器，只输出一句话。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=120,
                temperature=0.3,
            )
        except Exception:
            return None

    def _build_queries(self, payload: Dict[str, Any]) -> List[QuerySpec]:
        queries: List[QuerySpec] = []
        payload_json = json.dumps(payload, ensure_ascii=False)
        if payload_json:
            queries.append(QuerySpec(payload_json, "payload_json"))

        keywords: List[str] = []
        for key in (
            "doc_type",
            "type",
            "category",
            "expense_type",
            "invoice_type",
        ):
            if payload.get(key):
                keywords.append(str(payload[key]))

        vendor = payload.get("vendor") or payload.get("vendor_name")
        if vendor:
            keywords.append(str(vendor))

        currency = payload.get("currency")
        if currency:
            keywords.append(str(currency))

        amount = payload.get("total_amount") or payload.get("amount")
        if amount is not None:
            keywords.append(f"金额 {amount}")

        if keywords:
            queries.append(QuerySpec(" ".join(keywords), "keywords"))

        nl_query = self._build_nl_query(payload)
        if nl_query:
            queries.append(QuerySpec(nl_query, "nl_query"))

        # 兜底关键词，提升政策通用召回
        queries.append(QuerySpec("报销 票据 发票 费用 规则 限额 审批 差旅 餐饮 交通 住宿", "fallback"))
        return [q for q in queries if q.text.strip()]

    def _dedup(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        uniq: List[Dict[str, Any]] = []
        for item in results:
            fingerprint = (
                str(item.get("title", "")),
                str(item.get("summary", "")),
                str(item.get("content", "")),
            )
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            uniq.append(item)
        return uniq

    def _tag_score(self, item: Dict[str, Any], payload: Dict[str, Any]) -> float:
        score = 0.0
        if not item:
            return score
        expense_type = (str(item.get("expense_type")) or "").strip()
        scene = (str(item.get("scene")) or "").strip()
        city_level = (str(item.get("city_level")) or "").strip()

        if expense_type and str(payload.get("expense_type") or payload.get("doc_type") or "").find(expense_type) >= 0:
            score += 0.05
        if scene and str(payload.get("scene") or payload.get("category") or "").find(scene) >= 0:
            score += 0.05
        if city_level and str(payload.get("city_level") or payload.get("city") or "").find(city_level) >= 0:
            score += 0.03
        return score

    def retrieve(self, payload: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        返回拼接后的上下文字符串与命中的原始记录。
        """
        if not self.store.records:
            return "", []

        queries = self._build_queries(payload)
        candidates: List[Dict[str, Any]] = []
        for query in queries:
            weight = self.WEIGHTS.get(query.kind, 1.0)
            for k in self.top_ks:
                hits = self.store.similarity_search(query.text, top_k=k)
                for h in hits:
                    base = h.get("score", 0)
                    h["score"] = base * weight + self._tag_score(h, payload)
                    h["_q_kind"] = query.kind
                candidates.extend(hits)

        uniq = self._dedup(candidates)
        uniq.sort(key=lambda x: x.get("score", 0), reverse=True)

        fragments: List[str] = []
        kept: List[Dict[str, Any]] = []
        token_count = 0
        for idx, item in enumerate(uniq, start=1):
            text = item.get("summary") or item.get("content") or ""
            if not text.strip():
                continue
            evidence_id = f"R{idx}"
            snippet = f"[{evidence_id}] {item.get('title', '规则')}：{text}"
            est = _estimate_tokens(snippet)
            if token_count + est > self.max_tokens:
                break
            item["_evidence_id"] = evidence_id
            fragments.append(snippet)
            kept.append(item)
            token_count += est
            if len(kept) >= self.max_items:
                break

        return "\n---\n".join(fragments), kept


__all__ = ["RAGRetriever", "QuerySpec"]
