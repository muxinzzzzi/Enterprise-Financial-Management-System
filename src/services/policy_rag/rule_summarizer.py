from __future__ import annotations

from textwrap import dedent
from typing import Dict, List, Sequence, Tuple

from llm_client import LLMClient
from models.schemas import PolicyDocument

from .json_repair import repair_json


SUMMARY_PROMPT = dedent(
    """
    你是企业差旅/费用报销政策的摘要助手。
    请将以下政策压缩为要点，便于后续检索与判断：
    - 只保留额度、条件、例外、所需凭证等关键点
    - 使用简洁短句，中文输出
    - 最多 120 字
    标题：{title}
    原文：{content}
    """
)


class RuleSummarizer:
    """对政策做结构化摘要，提升后续 RAG 的可判别性。"""

    def __init__(self, llm: LLMClient, fallback_chars: int = 400) -> None:
        self.llm = llm
        self.fallback_chars = fallback_chars

    def _extract_tags(self, policy: PolicyDocument) -> Dict[str, str]:
        prompt = dedent(
            f"""
            请根据以下政策文本，提取简单标签并用JSON返回：
            - expense_type: 如 "出租车" "住宿" "餐饮" "机票" 等
            - scene: 如 "差旅" "市内交通" "加班打车"
            - city_level: "一线" "二线" "其他" 或留空
            只输出 JSON 对象。
            政策：{policy.content[:1500]}
            """
        )
        try:
            raw = self.llm.chat(
                [
                    {"role": "system", "content": "你是精简的标签抽取助手，只输出JSON。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200,
                temperature=0.2,
            )
            data = repair_json(raw, self.llm, schema_hint='{"expense_type": str, "scene": str, "city_level": str}')
            return {k: str(v) for k, v in data.items() if v} if isinstance(data, dict) else {}
        except Exception:
            return {}

    def summarize(self, policy: PolicyDocument) -> str:
        prompt = SUMMARY_PROMPT.format(
            title=policy.title,
            content=policy.content[:2000],
        )
        try:
            return self.llm.chat(
                [
                    {"role": "system", "content": "你是严谨的政策摘要助手"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200,
                temperature=0.2,
            )
        except Exception:
            # 当 LLM 不可用时，退化为截断原文
            return policy.content[: self.fallback_chars]

    def summarize_batch(self, policies: Sequence[PolicyDocument]) -> Tuple[List[str], List[dict]]:
        texts: List[str] = []
        metas: List[dict] = []
        for policy in policies:
            summary = self.summarize(policy)
            tags = self._extract_tags(policy)
            texts.append(summary)
            metas.append(
                {
                    "title": policy.title,
                    "content": policy.content,
                    "summary": summary,
                    "source": "policy",
                    **tags,
                }
            )
        return texts, metas


__all__ = ["RuleSummarizer"]
