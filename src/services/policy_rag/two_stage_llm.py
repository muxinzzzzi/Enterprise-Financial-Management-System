from __future__ import annotations

import json
from textwrap import dedent
from typing import Any, Dict, List

from llm_client import LLMClient

from .json_repair import repair_json


REASONING_PROMPT = dedent(
    """
    你将基于“政策规则 + 票据信息”进行合规性判断。
    严重程度定义：
    - HIGH：明确违反金额/对象/范围等硬性规定，应驳回报销
    - MEDIUM：信息缺失、不符合流程要求、需要补充材料或说明
    - LOW：基本符合，只是有建议或轻微风险

    规则编号说明：上下文中形如 [R1] [R2] 的编号是规则证据，后续引用时请使用这些编号。

    请逐条给出推理过程，不要输出 JSON。
    - 逐项列出规则要点与对应的票据信息
    - 标注是否符合/不符合/无法判断，并依据上述严重程度给出高/中/低
    - 若有例外或补充条件，请写出理由
    输出简洁中文推理列表，最后给出总体结论。
    规则：
    {rules}

    票据：
    {payload}
    """
)


JSON_PROMPT = dedent(
    """
    将上述推理结果转为严格 JSON 数组。
    字段：
    - rule_title: string
    - severity: "LOW" | "MEDIUM" | "HIGH"（按提示中的定义）
    - kind: "VIOLATION" | "MISSING_INFO" | "SUGGESTION"
    - message: string
    - references: string[] 可选，必须使用形如 "R1" "R2" 的规则编号
    若全部符合，返回空数组 []。
    只输出 JSON，本行以下不得出现额外文本。
    """
)


class TwoStageLLM:
    """二阶段推理，降低幻觉并确保 JSON 输出。"""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _reason(self, rules: str, payload: str) -> str:
        return self.llm.chat(
            [
                {"role": "system", "content": "你是严谨的报销政策审查员，先做推理后再给结论。"},
                {"role": "user", "content": REASONING_PROMPT.format(rules=rules, payload=payload)},
            ],
            max_tokens=800,
            temperature=0.2,
        )

    def _to_json(self, reasoning: str) -> Any:
        reply = self.llm.chat(
            [
                {"role": "system", "content": "你是结构化转换助手，严格按要求输出 JSON。"},
                {"role": "user", "content": f"{reasoning}\n\n{JSON_PROMPT}"},
            ],
            max_tokens=400,
            temperature=0.1,
        )
        schema_hint = (
            'JSON 数组元素形如: {"rule_title": str, "severity": "LOW"|"MEDIUM"|"HIGH", '
            '"kind": "VIOLATION"|"MISSING_INFO"|"SUGGESTION", "message": str, "references": [str]}'
        )
        return repair_json(reply, self.llm, schema_hint=schema_hint)

    def generate_flags_with_reasoning(self, rules: str, payload: Dict[str, Any]) -> tuple[List[Dict[str, Any]], str]:
        reasoning = self._reason(rules, json.dumps(payload, ensure_ascii=False))
        raw = self._to_json(reasoning)
        if not isinstance(raw, list):
            return [], reasoning
        flags: List[Dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            title = item.get("rule_title") or item.get("title") or "规则校验"
            severity = str(item.get("severity", "LOW")).upper()
            if severity not in {"LOW", "MEDIUM", "HIGH"}:
                severity = "LOW"
            kind = item.get("kind") or "VIOLATION"
            if kind not in {"VIOLATION", "MISSING_INFO", "SUGGESTION"}:
                kind = "VIOLATION"
            message = item.get("message") or item.get("description") or ""
            references = item.get("references") or []
            if isinstance(references, str):
                references = [references]
            flags.append(
                {
                    "rule_title": str(title),
                    "severity": severity,
                    "kind": kind,
                    "message": str(message),
                    "references": list(references) if isinstance(references, list) else [],
                }
            )
        return flags, reasoning

    def generate_flags(self, rules: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        flags, _ = self.generate_flags_with_reasoning(rules, payload)
        return flags


__all__ = ["TwoStageLLM"]




