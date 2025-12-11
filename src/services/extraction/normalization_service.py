"""语义归一与供应商解析。"""
from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, Optional

from rapidfuzz import fuzz

from config import Settings, get_settings


class NormalizationService:
    """字段归一化服务，保证后续 Analytics/规则引擎使用的数据稳定。"""

    def __init__(self, settings: Settings | None = None, vendor_cache_limit: int = 2000) -> None:
        self.settings = settings or get_settings()
        self.vendor_cache_limit = vendor_cache_limit
        self.vendor_lexicon: "OrderedDict[str, str]" = OrderedDict()

    def normalize(self, schema: Dict[str, Any], payload_meta: Dict[str, Any]) -> Dict[str, Any]:
        vendor = schema.get("vendor_name") or payload_meta.get("vendor_hint")
        canonical_vendor = self._canonicalize_vendor(vendor)
        currency = self._normalize_currency(schema.get("currency") or payload_meta.get("currency"))
        issue_date = self._normalize_date(schema.get("issue_date"))
        total_amount = self._to_float(schema.get("total_amount"))
        tax_amount = self._to_float(schema.get("tax_amount"))

        normalized = {
            **schema,
            "vendor_name": canonical_vendor,
            "currency": currency,
            "issue_date": issue_date,
            "total_amount": total_amount,
            "tax_amount": tax_amount,
        }
        return normalized

    def _canonicalize_vendor(self, vendor: Optional[str]) -> Optional[str]:
        vendor = self._sanitize_vendor(vendor)
        if not vendor:
            return None

        scores = {canonical: fuzz.token_set_ratio(vendor, alias) for alias, canonical in self.vendor_lexicon.items()}
        if scores:
            winner, score = max(scores.items(), key=lambda item: item[1])
            if score > 90:
                return winner
        self._remember_vendor(vendor, vendor)
        return vendor

    def _remember_vendor(self, alias: str, canonical: str) -> None:
        """维护有限大小的供应商词典，避免内存无限增长。"""
        if alias in self.vendor_lexicon:
            self.vendor_lexicon.pop(alias)
        self.vendor_lexicon[alias] = canonical
        if len(self.vendor_lexicon) > self.vendor_cache_limit:
            self.vendor_lexicon.popitem(last=False)

    def _sanitize_vendor(self, vendor: Optional[str]) -> Optional[str]:
        if not vendor:
            return None
        sanitized = re.sub(r"\s+", " ", vendor).strip()
        return sanitized or None

    def _normalize_date(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = value.replace("年", "-").replace("月", "-").replace("日", "")
        value = re.sub(r"[./]", "-", value)
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y%m%d"):
                try:
                    dt = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            else:
                return value
        return dt.date().isoformat()

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        sanitized = (
            str(value)
            .replace(",", "")
            .replace("，", "")
            .replace("￥", "")
            .replace("元", "")
            .strip()
        )
        negative = False
        if sanitized.startswith("(") and sanitized.endswith(")"):
            negative = True
            sanitized = sanitized[1:-1]
        if sanitized.startswith("（") and sanitized.endswith("）"):
            negative = True
            sanitized = sanitized[1:-1]
        try:
            amount = float(sanitized)
            return -amount if negative else amount
        except ValueError:
            return None

    def _normalize_currency(self, raw_value: Optional[str]) -> str:
        """统一货币编码，缺失时回退全局配置。"""
        if not raw_value:
            return self.settings.default_currency
        normalized = re.sub(r"[^A-Za-z]", "", raw_value).upper()
        return normalized or self.settings.default_currency


__all__ = ["NormalizationService"]
