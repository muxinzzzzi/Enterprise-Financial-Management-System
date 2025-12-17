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
TAXI_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/taxi_receipt"
TRAIN_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/train_ticket"
GENERAL_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"


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
        """兼容旧接口：直接按增值税入口调用，失败时降级通用。"""
        token = self._access_token()
        image_bytes = self._read_bytes(file)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        data = {
            "image": image_b64,
            "accuracy": "high",
            "multi_detect": "true",
        }
        try:
            payload = self._call_api(OCR_URL, token, data)
        except BaiduOCRException as exc:
            if "282103" in str(exc) or "failed to match the template" in str(exc):
                payload = self._call_general(token, image_b64)
            else:
                raise
        return self._package_payload(payload)

    def recognize_smart(self, file: Union[Path, bytes, BinaryIO]) -> Dict[str, Any]:
        """
        先通用OCR获取文本做类型判定，再分流到增值税/出租车/火车票接口，最后兜底通用。
        """
        token = self._access_token()
        image_bytes = self._read_bytes(file)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # 1) 通用文字识别
        general_payload = self._call_general(token, image_b64)
        general_text, _ = self._extract_text_and_fields(general_payload)
        doc_type = self._classify_doc_type(general_text)

        # 2) 分流
        if doc_type == "taxi":
            try:
                specific = self._call_api(TAXI_URL, token, {"image": image_b64})
                specific["engine"] = "baidu_taxi_receipt"
                return self._package_payload(specific)
            except Exception:
                pass
        elif doc_type == "train":
            try:
                specific = self._call_api(TRAIN_URL, token, {"image": image_b64})
                specific["engine"] = "baidu_train_ticket"
                return self._package_payload(specific)
            except Exception:
                pass
        else:
            try:
                specific = self._call_api(
                    OCR_URL,
                    token,
                    {
                        "image": image_b64,
                        "accuracy": "high",
                        "multi_detect": "true",
                    },
                )
                specific["engine"] = "baidu_invoice_ocr"
                return self._package_payload(specific)
            except Exception:
                pass

        # 3) 兜底用通用结果
        general_payload["engine"] = "baidu_general_basic"
        return self._package_payload(general_payload)

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

    def _call_api(self, url: str, token: str, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = self._session.post(
                f"{url}?access_token={token}",
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
        return payload

    def _call_general(self, token: str, image_b64: str) -> Dict[str, Any]:
        """通用文字识别：用于前置分类或兜底。"""
        payload = self._call_api(GENERAL_URL, token, {"image": image_b64})
        payload["engine"] = "baidu_general_basic"
        return payload

    @staticmethod
    def _extract_confidence(payload: Dict[str, Any]) -> float:
        prob = payload.get("probability")
        if isinstance(prob, dict) and prob.get("average") is not None:
            try:
                return float(prob.get("average", 0.0))
            except (TypeError, ValueError):
                return 0.0
        # 通用文字识别无 probability 字段，给一个保守默认值以避免被 layout-text 低信度覆盖
        if payload.get("engine") == "baidu_general_basic":
            return 0.8
        return 0.0

    def _classify_doc_type(self, text: str) -> str:
        t = text or ""
        if any(k in t for k in ["出租车", "出租汽车", "上车时间", "下车时间", "车牌号", "单价", "里程"]):
            return "taxi"
        if any(k in t for k in ["火车", "车次", "动车", "高铁", "检票口", "始发站", "到达站"]):
            return "train"
        return "vat"

    def _package_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        text, fields = self._extract_text_and_fields(payload)
        confidence = self._extract_confidence(payload)
        return {
            "engine": payload.get("engine", "baidu_invoice_ocr"),
            "text": text,
            "confidence": confidence,
            "fields": fields,
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
                raise BaiduOCRException(f"获取百度OCR token 失败: {exc}") from exc

            payload = response.json()
            self._token = payload.get("access_token")
            expires_in = int(payload.get("expires_in", 0))
            self._token_expire_ts = now + max(expires_in - 60, 0)
            if not self._token:
                raise BaiduOCRException("无法获取百度OCR access_token")
            return self._token


__all__ = ["BaiduInvoiceOCRClient", "BaiduOCRException"]
