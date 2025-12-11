"""Baidu 发票识别 OCR 客户端。"""
from __future__ import annotations

import base64
import threading
import time
from pathlib import Path
from typing import Any, BinaryIO, Dict, Union

import requests

from config import get_settings


TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice"


class BaiduOCRException(Exception):
    """百度 OCR 调用异常。"""


class BaiduInvoiceOCRClient:
    def __init__(self, app_id: str, api_key: str, secret_key: str) -> None:
        self.app_id = app_id
        self.api_key = api_key
        self.secret_key = secret_key
        self._token: str | None = None
        self._token_expire_ts: float = 0.0
        self._lock = threading.Lock()
        self._session = requests.Session()

    @classmethod
    def from_settings(cls) -> "BaiduInvoiceOCRClient":
        settings = get_settings()
        if not (settings.baidu_app_id and settings.baidu_api_key and settings.baidu_secret_key):
            raise RuntimeError("百度OCR配置缺失，请设置 baidu_app_id / baidu_api_key / baidu_secret_key")
        return cls(settings.baidu_app_id, settings.baidu_api_key, settings.baidu_secret_key)

    def recognize(self, file: Union[Path, bytes, BinaryIO]) -> Dict[str, Any]:
        token = self._access_token()
        image_bytes = self._read_bytes(file)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        data = {
            "image": image_b64,
            "accuracy": "high",
            "multi_detect": "true",
        }
        try:
            response = self._session.post(
                f"{OCR_URL}?access_token={token}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=data,
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise BaiduOCRException(f"请求百度OCR失败: {exc}") from exc

        payload = response.json()
        if "error_code" in payload:
            raise BaiduOCRException(f"Baidu OCR error {payload.get('error_code')}: {payload.get('error_msg')}")

        text, fields = self._extract_text_and_fields(payload)
        confidence = self._extract_confidence(payload)

        return {
            "engine": "baidu_invoice_ocr",
            "text": text,
            "confidence": confidence,
            "fields": fields,
            "raw": payload,
            "app_id": self.app_id,
        }

    def _extract_text_and_fields(self, payload: Dict[str, Any]) -> tuple[str, Dict[str, str]]:
        words_result = payload.get("words_result", [])
        fields: Dict[str, str] = {}

        if isinstance(words_result, list):
            words = [item.get("words", "") for item in words_result if isinstance(item, dict)]
            text = "\n".join(filter(None, words))
        elif isinstance(words_result, dict):
            lines = []

            def pick(key: str) -> str:
                item = words_result.get(key)
                if isinstance(item, dict):
                    return str(item.get("words") or "").strip()
                return str(item or "").strip()

            fields = {
                "invoice_code": pick("InvoiceCode"),
                "invoice_num": pick("InvoiceNum"),
                "issue_date": pick("InvoiceDate"),
                "total_amount": pick("TotalAmount"),
                "tax_amount": pick("TaxAmount"),
                "buyer_name": pick("PurchaserName"),
                "seller_name": pick("SellerName"),
            }
            for key, val in fields.items():
                if val:
                    lines.append(f"{key}: {val}")
            text = "\n".join(lines)
        else:
            text = ""

        return text, fields

    @staticmethod
    def _extract_confidence(payload: Dict[str, Any]) -> float:
        prob = payload.get("probability")
        if isinstance(prob, dict) and prob.get("average") is not None:
            try:
                return float(prob.get("average", 0.0))
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    def _read_bytes(self, file: Union[Path, bytes, BinaryIO]) -> bytes:
        if isinstance(file, Path):
            return file.read_bytes()
        if isinstance(file, bytes):
            return file
        return file.read()

    def _access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expire_ts - 30:
            return self._token

        with self._lock:
            now = time.time()
            if self._token and now < self._token_expire_ts - 30:
                return self._token

            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key,
            }
            try:
                response = self._session.post(TOKEN_URL, params=params, timeout=10)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise BaiduOCRException(f"获取百度OCR token 失败: {exc}") from exc

            payload = response.json()
            self._token = payload.get("access_token")
            expires_in = int(payload.get("expires_in", 0))
            self._token_expire_ts = now + max(expires_in - 60, 0)
            if not self._token:
                raise BaiduOCRException("无法获取百度OCR access_token")
            return self._token


__all__ = ["BaiduInvoiceOCRClient", "BaiduOCRException"]
