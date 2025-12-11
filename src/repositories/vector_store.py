"""轻量向量存储，兼容真实嵌入与降级方案。"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import numpy as np

from config import get_settings


@dataclass
class VectorRecord:
    vector: np.ndarray
    metadata: Dict[str, Any]


class VectorStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.model = None
        self.records: List[VectorRecord] = []
        self._dim = 384
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self.model = SentenceTransformer(self.settings.embedding_model)
            sample = self.model.encode(["init"], convert_to_numpy=True)
            self._dim = int(sample.shape[1]) if sample.ndim == 2 else len(sample)
        except Exception:
            self.model = None

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dim))
        if self.model is not None:
            return self.model.encode(list(texts), convert_to_numpy=True)
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
            repeat = (self._dim + len(digest) - 1) // len(digest)
            raw = (digest * repeat)[: self._dim]
            vec = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            vec = (vec - vec.mean()) / (vec.std() + 1e-6)
            vectors.append(vec)
        return np.vstack(vectors)

    def add_texts(self, texts: Sequence[str], metadatas: Sequence[Dict[str, Any]]) -> None:
        if not texts:
            return
        vectors = self._embed(texts)
        for vec, meta in zip(vectors, metadatas):
            self.records.append(VectorRecord(vector=vec, metadata=meta))

    def similarity_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.records:
            return []
        query_vec = self._embed([query])[0]
        query_norm = np.linalg.norm(query_vec) + 1e-9
        results = []
        for record in self.records:
            score = float(np.dot(query_vec, record.vector) / (query_norm * (np.linalg.norm(record.vector) + 1e-9)))
            results.append((score, record.metadata))
        results.sort(key=lambda item: item[0], reverse=True)
        return [
            {"score": round(score, 4), **metadata}
            for score, metadata in results[:top_k]
        ]

    def clear(self) -> None:
        self.records.clear()


__all__ = ["VectorStore"]
