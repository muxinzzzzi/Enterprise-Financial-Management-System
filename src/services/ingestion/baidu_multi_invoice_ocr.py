"""Baidu 多票据智能识别（自动分类 13 类票据）。"""
from __future__ import annotations

import base64
import threading
import time
from pathlib import Path
from typing import Any, BinaryIO, Dict, Union

import requests

from config import get_settings


TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
MULTI_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/multiple_invoice"


class BaiduMultiInvoiceException(Exception):
    """百度多票据识别异常。"""


class BaiduMultipleInvoiceClient:
    def __init__(self, app_id: str, api_key: str, secret_key: str) -> None:
        self.app_id = app_id
        self.api_key = api_key
        self.secret_key = secret_key
        self._token: str | None = None
        self._token_expire_ts: float = 0.0
        self._lock = threading.Lock()
        self._session = requests.Session()

    @classmethod
    def from_settings(cls) -> "BaiduMultipleInvoiceClient":
        settings = get_settings()
        if not (settings.baidu_app_id and settings.baidu_api_key and settings.baidu_secret_key):
            raise RuntimeError("百度OCR配置缺失，请设置 baidu_app_id / baidu_api_key / baidu_secret_key")
        return cls(settings.baidu_app_id, settings.baidu_api_key, settings.baidu_secret_key)

    def recognize(self, file: Union[Path, bytes, BinaryIO]) -> Dict[str, Any]:
        token = self._access_token()
        image_bytes = self._read_bytes(file)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        payload = self._call_api(MULTI_URL, token, {"image": image_b64})

        # multiple_invoice 返回 words_result: list，每个元素带 invoice_type + result/words_result
        text_lines = []
        invoice_type = None
        confidence = 0.0
        structured_fields: Dict[str, Any] = {}

        results = payload.get("words_result") or []
        if isinstance(results, list) and results:
            first = results[0]
            invoice_type = first.get("invoice_type") or first.get("type")

            # 结构化字段（如出租车票的 InvoiceNum / Date / Fare 等）
            result_fields = first.get("result") or {}
            if isinstance(result_fields, dict):
                structured_fields["result"] = result_fields
                # 将主要字段拼成文本，便于预览
                for k, v in result_fields.items():
                    if v is None:
                        continue
                    text_lines.append(f"{k}:{v}")

            # 行级 words_result（部分类型提供逐行文字）
            inner = first.get("words_result") or []
            if isinstance(inner, list):
                structured_fields["words_result"] = inner
                for item in inner:
                    if not isinstance(item, dict):
                        continue
                    val = item.get("words") or item.get("word") or item.get("value") or ""
                    name = item.get("name")
                    if val:
                        if name:
                            text_lines.append(f"{name}:{val}")
                        else:
                            text_lines.append(str(val))

            # 置信度
            if first.get("probability"):
                try:
                    confidence = float(first["probability"])
                except Exception:
                    confidence = 0.0

        text = "\n".join(filter(None, text_lines))

        return {
            "engine": "baidu_multiple_invoice",
            "text": text,
            "confidence": confidence or 0.85,  # 默认较高，避免被占位覆盖
            "fields": {
                "invoice_type": invoice_type,
                "structured": structured_fields,
            },
            "raw": payload,
            "app_id": self.app_id,
        }

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
                raise BaiduMultiInvoiceException(f"获取百度OCR token 失败: {exc}") from exc

            payload = response.json()
            self._token = payload.get("access_token")
            expires_in = int(payload.get("expires_in", 0))
            self._token_expire_ts = now + max(expires_in - 60, 0)
            if not self._token:
                raise BaiduMultiInvoiceException("无法获取百度OCR access_token")
            return self._token

    def _call_api(self, url: str, token: str, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = self._session.post(
                f"{url}?access_token={token}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=data,
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise BaiduMultiInvoiceException(f"请求百度多票据OCR失败: {exc}") from exc

        payload = resp.json()
        if "error_code" in payload:
            raise BaiduMultiInvoiceException(
                f"Baidu multiple_invoice error {payload.get('error_code')}: {payload.get('error_msg')}"
            )
        return payload


__all__ = ["BaiduMultipleInvoiceClient", "BaiduMultiInvoiceException"]

