"""多引擎OCR与置信度融合。"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from config import get_settings
from llm_client import LLMClient
from models.schemas import OCRSpan
from services.ingestion.baidu_invoice_ocr import BaiduInvoiceOCRClient

try:  # 可选依赖，缺失时自动跳过增强处理
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # noqa: BLE001
    cv2 = None
    np = None


class MultiEngineOCRService:
    """
    支持：
      1. 调用多个OCR HTTP接口（逐页，优先使用渲染后的 image_path）
      2. 自动倾斜检测与旋转纠偏（OCR引擎角度优先，OpenCV 兜底）
      3. 可选 LLM 投票融合
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.settings = get_settings()
        self.endpoints = self.settings.ocr_endpoints
        self.llm = llm_client
        self.use_llm = bool(llm_client and getattr(llm_client, "enabled", False))
        try:
            self.baidu_client = BaiduInvoiceOCRClient.from_settings()
        except Exception:
            self.baidu_client = None

    def recognize(self, ingestion_payload: Dict[str, Any]) -> Dict[str, Any]:
        original_file = Path(ingestion_payload["file_path"])
        pages = ingestion_payload.get("pages") or []
        page_results: List[Dict[str, Any]] = []

        for idx, page in enumerate(pages):
            page_path = Path(page.get("image_path") or original_file)
            image_bytes, _ = self._prepare_image_bytes(page_path)
            candidates = []

            for endpoint in self.endpoints:
                try:
                    cand = self._request_ocr(endpoint, image_bytes, page_path.name)
                    angle = cand.pop("angle", 0.0) or 0.0
                    if abs(angle) > 0.5:
                        rotated_bytes = self._rotate_image_bytes(image_bytes, angle)
                        improved = self._request_ocr(endpoint, rotated_bytes, page_path.name)
                        improved["engine"] = cand["engine"]
                        improved["rotation_correction"] = angle
                        cand = improved if improved.get("confidence", 0.0) >= cand.get("confidence", 0.0) else cand
                    candidates.append(cand)
                except Exception:
                    continue

            if self.baidu_client:
                try:
                    candidates.append(self._request_baidu(image_bytes))
                except Exception:
                    pass

            if ingestion_payload.get("text_blocks"):
                baseline_text = ingestion_payload["text_blocks"][min(idx, len(ingestion_payload["text_blocks"]) - 1)]
                candidates.append({"engine": "layout-text", "text": baseline_text, "confidence": 0.45})

            fused = self._fuse_candidates(candidates)
            spans = [
                OCRSpan(
                    text=segment.strip(),
                    confidence=fused["confidence"],
                    engine=fused["engine"],
                )
                for segment in fused["text"].split("\n")
                if segment.strip()
            ]
            page_results.append(
                {
                    "text": fused["text"],
                    "spans": spans,
                    "confidence": fused["confidence"],
                    "engine": fused["engine"],
                }
            )

        full_text = "\n".join(page["text"] for page in page_results)
        avg_conf = sum(page["confidence"] for page in page_results) / max(len(page_results), 1)
        spans = [span for page in page_results for span in page["spans"]]

        return {
            "text": full_text,
            "confidence": round(avg_conf, 4),
            "spans": spans,
        }

    def _request_ocr(self, endpoint: str, image_bytes: bytes, file_name: str) -> Dict[str, Any]:
        payload = {
            "file_name": file_name,
            "content_base64": base64.b64encode(image_bytes).decode("utf-8"),
        }
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return {
            "engine": endpoint,
            "text": data.get("text", ""),
            "confidence": float(data.get("confidence", 0.7)),
            "angle": self._extract_angle(data),
        }

    def _request_baidu(self, image_bytes: bytes) -> Dict[str, Any]:
        if not self.baidu_client:
            raise RuntimeError("Baidu OCR 未配置")
        result = self.baidu_client.recognize(image_bytes)
        return {"engine": result["engine"], "text": result["text"], "confidence": result.get("confidence", 0.8)}

    # ---------- 图像准备与旋转纠偏 ---------- #
    def _prepare_image_bytes(self, image_path: Path) -> Tuple[bytes, float]:
        """返回纠偏后的 JPEG 字节与应用角度（OpenCV 兜底）。"""
        if not image_path.exists():
            return b"", 0.0
        if cv2 is None or np is None:
            return image_path.read_bytes(), 0.0

        try:
            img = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                return image_path.read_bytes(), 0.0

            angle = self._estimate_skew_angle(img)
            if abs(angle) > 0.1:
                img = self._rotate_cv_image(img, angle)
            ok, encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            return (encoded.tobytes() if ok else image_path.read_bytes(), angle if ok else 0.0)
        except Exception:
            return image_path.read_bytes(), 0.0

    def _rotate_image_bytes(self, image_bytes: bytes, angle: float) -> bytes:
        if abs(angle) < 0.1:
            return image_bytes
        if cv2 is None or np is None:
            return image_bytes
        try:
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return image_bytes
            rotated = self._rotate_cv_image(img, angle)
            ok, encoded = cv2.imencode(".jpg", rotated, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            return encoded.tobytes() if ok else image_bytes
        except Exception:
            return image_bytes

    def _estimate_skew_angle(self, img: "np.ndarray") -> float:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        coords = cv2.findNonZero(255 - thresh)
        angle = 0.0
        if coords is not None:
            rect = cv2.minAreaRect(coords)
            angle = rect[-1]
            if angle < -45:
                angle = 90 + angle
        return angle

    def _rotate_cv_image(self, img: "np.ndarray", angle: float) -> "np.ndarray":
        center = tuple(np.array(img.shape[1::-1]) / 2)
        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            img,
            rot_mat,
            img.shape[1::-1],
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )

    # ---------- 角度提取与融合 ---------- #
    @staticmethod
    def _extract_angle(data: Dict[str, Any]) -> float:
        """兼容多种 OCR 返回字段：rotation/direction/angle/orientation."""
        for key in ("rotation", "direction", "angle", "orientation"):
            val = data.get(key)
            if val is None:
                continue
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
        return 0.0

    def _fuse_candidates(self, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not candidates:
            return {"engine": "empty", "text": "", "confidence": 0.0}
        if len(candidates) == 1 or not self.use_llm:
            return max(candidates, key=lambda item: item.get("confidence", 0.0))

        prompt = "\n".join(
            f"候选{idx+1} (engine={cand['engine']}, conf={cand['confidence']:.2f}):\n{cand['text']}"
            for idx, cand in enumerate(candidates)
        )
        reply = self.llm.chat(
            [
                {"role": "system", "content": "你是OCR仲裁器，选择语义最合理的候选"},
                {"role": "user", "content": prompt + "\n只需回复被选候选的编号"},
            ]
        )
        try:
            winner_idx = int("".join(ch for ch in reply if ch.isdigit())) - 1
            return candidates[max(0, min(winner_idx, len(candidates) - 1))]
        except Exception:
            return max(candidates, key=lambda item: item.get("confidence", 0.0))


__all__ = ["MultiEngineOCRService"]
