from __future__ import annotations

import json
from typing import Any, Callable, List, Optional

from llm_client import LLMClient


def repair_json(
    raw: str,
    llm: LLMClient,
    schema_hint: str = "",
    logger: Optional[Callable[[str], None]] = None,
    max_len: int = 50_000,
) -> Any:
    """
    尝试容错解析 LLM JSON 输出；失败时用 LLM 纠正，并做长度保护。
    """
    if len(raw) > max_len:
        return []
    try:
        return json.loads(raw)
    except Exception:
        pass

    prompt_lines: List[str] = [
        "请把下面内容修复为严格合法的 JSON。",
        "仅返回 JSON 字符串，不要添加解释或 Markdown。",
    ]
    if schema_hint:
        prompt_lines.append(f"JSON 结构要求：{schema_hint}")
    prompt_lines.append(f"原始内容：\n{raw}")
    prompt = "\n".join(prompt_lines)

    fixed = llm.chat(
        [
            {"role": "system", "content": "你是严谨的 JSON 修复器，只输出合法 JSON。"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=400,
        temperature=0.1,
    )
    if logger:
        logger(f"[repair_json] raw={raw[:4000]}\nfixed={fixed[:4000]}")
    if len(fixed) > max_len:
        return []
    try:
        return json.loads(fixed)
    except Exception:
        return []


__all__ = ["repair_json"]
