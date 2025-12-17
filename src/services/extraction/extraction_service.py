"""LLM字段抽取与schema归一。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

from llm_client import LLMClient
from utils.prompts import FIELD_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class FieldExtractionService:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    def extract(self, ocr_payload: Dict[str, Any]) -> Dict[str, Any]:
        text = ocr_payload.get("text", "") or ""
        prompt = self._build_prompt(text)
        schema = self._default_schema()
        try:
            reply = self.llm.chat(
                [
                    {"role": "system", "content": "你是票据解析专家，输出JSON"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1200,
                temperature=0,
                response_format={"type": "json_object"},
            )
            data = json.loads(self._extract_json_block(reply))
        except json.JSONDecodeError as exc:
            logger.warning("LLM 返回非 JSON，回退 regex：%s", exc)
            return self._regex_fallback(text)
        except Exception as exc:  # noqa: BLE001
            logger.exception("字段抽取 LLM 调用失败，回退 regex")
            return self._regex_fallback(text)

        for key in schema.keys():
            if key in {"line_items", "unknown_fields"}:
                continue
            schema[key] = self._normalize_field(key, data.get(key))

        if isinstance(data.get("line_items"), list):
            schema["line_items"] = data["line_items"]

        if isinstance(data.get("unknown_fields"), list):
            schema["unknown_fields"] = data["unknown_fields"]
        else:
            schema["unknown_fields"] = self._extract_unknown_fields(text, schema)

        return schema

    def _build_prompt(self, text: str) -> str:
        """构造带边界标记的 prompt，避免截断关键字段。"""
        max_len = 6000
        if len(text) > max_len:
            head = text[:4000]
            tail = text[-2000:]
            clipped = f"{head}\n...[OCR截断]...\n{tail}"
        else:
            clipped = text

        return (
            f"{FIELD_EXTRACTION_PROMPT}\n\n"
            "### OCR_TEXT_BEGIN\n"
            f"{clipped}\n"
            "### OCR_TEXT_END"
        )

    def _default_schema(self) -> Dict[str, Any]:
        return {
            "invoice_number": None,
            "vendor_name": None,
            "tax_id": None,
            "issue_date": None,
            "currency": None,
            "total_amount": None,
            "tax_amount": None,
            "line_items": [],
            "notes": None,
            "unknown_fields": [],
        }

    def _normalize_field(self, key: str, value: Any) -> Any:
        if value is None:
            return None

        if key in {"total_amount", "tax_amount"}:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                cleaned = re.sub(r"[^\d\.\-]", "", value.replace(",", ""))
                try:
                    return float(cleaned)
                except ValueError:
                    return value

        if key == "invoice_number" and isinstance(value, str):
            return value.strip().replace(" ", "")

        if key == "currency" and isinstance(value, str):
            upper = value.strip().upper()
            if upper in {"￥", "¥", "RMB", "CNY", "人民币"}:
                return "CNY"
            return upper

        if key == "issue_date":
            return self._normalize_date(str(value))

        return value

    def _normalize_date(self, value: str | None) -> str | None:
        if not value:
            return None
        match = re.search(r"(20\d{2})[年/-]?(\d{1,2})[月/-]?(\d{1,2})", value)
        if match:
            return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        return value

    def _extract_json_block(self, text: str) -> str:
        if not text:
            return "{}"
        block = re.search(r"\{[\s\S]*\}", text)
        return block.group(0) if block else text

    def _extract_unknown_fields(self, text: str, schema: Dict[str, Any]) -> list[str]:
        result: list[str] = []
        lowered = text.lower()
        for key, val in schema.items():
            if key in {"unknown_fields", "line_items"}:
                continue
            if val is None and key and key.lower() in lowered:
                result.append(key)
        return result

    def _regex_fallback(self, text: str) -> Dict[str, Any]:
        schema = self._default_schema()
        patterns = {
            "invoice_number": r"(?:发票号码|票据号码)[:：]?\s*([0-9A-Za-z\-]+)",
            "tax_id": r"(?:纳税人识别号|税号)[:：]?\s*([0-9A-Z]{10,})",
            "total_amount": r"(?:合计|价税合计)[:：]?\s*([¥￥]?[0-9,]+\.\d{2})",
            "tax_amount": r"(?:税额|税款)[:：]?\s*([¥￥]?[0-9,]+\.\d{2})",
            "issue_date": r"(20\d{2}[年/-]\d{1,2}[月/-]\d{1,2}日?)",
            "currency": r"(?:币种|货币)[:：]?\s*([A-Z]{3}|人民币|CNY|RMB|¥|￥)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                schema[key] = self._normalize_field(key, match.group(1))

        vendor_match = re.search(r"(?:公司|单位|学院|医院|科技)[^\n]{2,30}", text)
        if vendor_match:
            schema["vendor_name"] = vendor_match.group(0).strip()

        heuristics = {
            "滴滴": "滴滴出行",
            "快车": "滴滴出行",
            "顺风车": "滴滴出行",
            "美团": "美团",
            "饿了么": "饿了么",
            "高德打车": "高德打车",
        }
        for keyword, vendor in heuristics.items():
            if keyword in text and not schema["vendor_name"]:
                schema["vendor_name"] = vendor
                break

        schema["unknown_fields"] = self._extract_unknown_fields(text, schema)
        return schema


__all__ = ["FieldExtractionService"]
