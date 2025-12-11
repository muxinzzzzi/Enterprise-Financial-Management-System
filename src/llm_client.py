"""统一的LLM客户端封装。"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from openai import OpenAI


class LLMClient:
    def __init__(self, model: str | None = None, api_key: str | None = None, base_url: str | None = None) -> None:
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or ""
        base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.enabled = bool(api_key)
        self.client = OpenAI(api_key=api_key or "", base_url=base_url)

    def chat(self, messages: List[dict[str, str]], **kwargs: Any) -> str:
        if not self.enabled:
            raise RuntimeError("LLM未配置 API Key")
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 512),
        }
        if kwargs.get("response_format"):
            params["response_format"] = kwargs["response_format"]

        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content.strip()

    def chat_json(self, messages: List[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        reply = self.chat(messages, **kwargs)
        try:
            return json.loads(reply)
        except json.JSONDecodeError:
            return {"raw": reply}


__all__ = ["LLMClient"]
