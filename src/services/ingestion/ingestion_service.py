"""文档接入与版面分析服务。"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pdfplumber
from PIL import Image, ImageOps

from config import DATA_DIR, get_settings
from models.schemas import DocumentPayload
from utils.file_ops import save_base64_file

try:  # 可选依赖，缺失时自动跳过区域检测
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # noqa: BLE001
    cv2 = None
    np = None

logger = logging.getLogger(__name__)


@dataclass
class PageSlice:
    page_number: int
    width: float
    height: float
    bbox: Dict[str, float]
    content_pointer: str
    image_path: str
    rotation: int
    is_scan: bool
    text: str
    tables: List[Dict[str, float]]
    seals: List[Dict[str, float]]
    qrcodes: List[Dict[str, float]]


class DocumentIngestionService:
    """负责接收原始票据、执行版面预处理、产出OCR就绪输入。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.page_output_dir = DATA_DIR / "output" / "pages"
        self.page_output_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self, payload: DocumentPayload) -> Dict[str, Any]:
        """入口：接收base64，落地文件，生成 per-page 图像与基础版面信息。"""
        document_id = payload.document_id()
        try:
            file_path = save_base64_file(payload.file_name, payload.file_content_base64, sub_dir="input")
            file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()  # noqa: S324
        except Exception as exc:  # noqa: BLE001
            logger.exception("保存上传文件失败")
            return {"document_id": document_id, "error": f"save_failed: {exc}"}

        extension = file_path.suffix.lower()
        try:
            if extension == ".pdf":
                result = self._process_pdf(file_path, document_id)
            else:
                result = self._process_image(file_path, document_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("ingestion 处理失败")
            return {
                "document_id": document_id,
                "file_path": str(file_path),
                "extension": extension,
                "error": f"ingestion_failed: {exc}",
            }

        result.update(
            {
                "document_id": document_id,
                "file_path": str(file_path),
                "extension": extension,
                "file_hash_md5": file_hash,
                "meta": payload.meta,
            }
        )
        return result

    # ---------------- internal helpers ---------------- #
    def _process_pdf(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        pages: List[PageSlice] = []
        text_blocks: List[str] = []
        structured_text_blocks: List[Dict[str, Any]] = []
        scanned_pages = 0
        landscape_pages = 0
        has_table = False

        with pdfplumber.open(file_path) as pdf:
            for index, page in enumerate(pdf.pages):
                text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                text_blocks.append(text)

                # 轻量判定扫描件
                is_scan = len(text.strip()) < 20
                if is_scan:
                    scanned_pages += 1

                # 版式属性
                if page.width > page.height:
                    landscape_pages += 1
                if not has_table:
                    try:
                        has_table = bool(page.extract_tables())
                    except Exception:
                        has_table = False

                # 渲染为图像并做预处理
                page_image = page.to_image(resolution=200).original
                processed, rotation = self._preprocess_image(page_image)
                image_path = self._save_page_image(processed, file_path.stem, index + 1, document_id)

                words = page.extract_words() or []
                regions = self._detect_regions(processed)

                structured_text_blocks.append(
                    {
                        "page_number": index + 1,
                        "text": text,
                        "words": [
                            {
                                "text": w.get("text", ""),
                                "bbox": {
                                    "x0": float(w.get("x0", 0.0)),
                                    "y0": float(w.get("top", 0.0)),
                                    "x1": float(w.get("x1", 0.0)),
                                    "y1": float(w.get("bottom", 0.0)),
                                },
                            }
                            for w in words
                        ],
                    }
                )

                pages.append(
                    PageSlice(
                        page_number=index + 1,
                        width=page.width,
                        height=page.height,
                        bbox={"x0": 0, "y0": 0, "x1": page.width, "y1": page.height},
                        content_pointer=f"{file_path.name}#page={index+1}",
                        image_path=str(image_path),
                        rotation=rotation,
                        is_scan=is_scan,
                        text=text,
                        tables=regions["tables"],
                        seals=regions["seals"],
                        qrcodes=regions["qrcodes"],
                    )
                )

        layout_summary = {
            "page_count": len(pages),
            "average_width": sum(p.width for p in pages) / max(len(pages), 1),
            "average_height": sum(p.height for p in pages) / max(len(pages), 1),
            "scanned_pages": scanned_pages,
            "scan_ratio": round(scanned_pages / max(len(pages), 1), 4),
            "landscape_pages": landscape_pages,
            "has_table": has_table or any(p.tables for p in pages),
        }

        return {
            "pages": [page.__dict__ for page in pages],
            "text_blocks": text_blocks,
            "structured_text_blocks": structured_text_blocks,
            "layout": layout_summary,
        }

    def _process_image(self, file_path: Path, document_id: str) -> Dict[str, Any]:
        raw_image = Image.open(file_path)
        processed, rotation = self._preprocess_image(raw_image)
        image_path = self._save_page_image(processed, file_path.stem, 1, document_id)
        regions = self._detect_regions(processed)

        pages = [
            PageSlice(
                page_number=1,
                width=float(processed.width),
                height=float(processed.height),
                bbox={"x0": 0, "y0": 0, "x1": float(processed.width), "y1": float(processed.height)},
                content_pointer=file_path.name,
                image_path=str(image_path),
                rotation=rotation,
                is_scan=True,
                text="",
                tables=regions["tables"],
                seals=regions["seals"],
                qrcodes=regions["qrcodes"],
            )
        ]
        text_blocks = ["来自图像的OCR待识别内容"]
        layout_summary = {
            "page_count": 1,
            "average_width": float(processed.width),
            "average_height": float(processed.height),
            "scanned_pages": 1,
            "scan_ratio": 1.0,
            "landscape_pages": 1 if processed.width > processed.height else 0,
            "has_table": False,
        }

        return {
            "pages": [page.__dict__ for page in pages],
            "text_blocks": text_blocks,
            "structured_text_blocks": [
                {"page_number": 1, "text": "", "words": []},
            ],
            "layout": layout_summary,
        }

    def _preprocess_image(self, image: Image.Image) -> Tuple[Image.Image, int]:
        """统一图像预处理：EXIF 旋转校正、RGB、尺寸约束。"""
        rotation = 0
        try:
            image, rotation = self._apply_exif_orientation(image)
        except Exception:
            rotation = 0

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
        if image.mode == "RGBA":
            image = image.convert("RGB")

        image = self._resize_long_edge(image, max_edge=2000)
        return image, rotation

    def _apply_exif_orientation(self, image: Image.Image) -> Tuple[Image.Image, int]:
        """按 EXIF 方向自动旋转，返回旋转角度。"""
        rotation = 0
        try:
            exif = image.getexif()
        except Exception:
            return image, rotation
        orientation = exif.get(274) if exif else None  # 274 == Orientation
        if orientation in (3, 6, 8):
            if orientation == 3:
                rotation = 180
                image = image.rotate(180, expand=True)
            elif orientation == 6:
                rotation = 270
                image = image.rotate(270, expand=True)
            elif orientation == 8:
                rotation = 90
                image = image.rotate(90, expand=True)
        image = ImageOps.exif_transpose(image)
        return image, rotation

    def _resize_long_edge(self, image: Image.Image, max_edge: int) -> Image.Image:
        width, height = image.size
        long_edge = max(width, height)
        if long_edge <= max_edge:
            return image
        scale = max_edge / long_edge
        new_size = (int(width * scale), int(height * scale))
        return image.resize(new_size, Image.Resampling.LANCZOS)

    def _save_page_image(self, image: Image.Image, stem: str, page_number: int, document_id: str) -> Path:
        target_dir = self.page_output_dir / document_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{stem}_page{page_number}.jpg"
        image.save(target_path, format="JPEG", quality=85, optimize=True)
        return target_path

    # ---------- 轻量区域检测（表格/章/二维码） ---------- #
    def _detect_regions(self, image: Image.Image) -> Dict[str, List[Dict[str, float]]]:
        if cv2 is None or np is None:
            return {"tables": [], "seals": [], "qrcodes": []}
        try:
            bgr = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        except Exception:
            return {"tables": [], "seals": [], "qrcodes": []}

        tables = self._detect_tables(bgr)
        seals = self._detect_red_seals(bgr)
        qrcodes = self._detect_qrcodes(bgr)
        return {"tables": tables, "seals": seals, "qrcodes": qrcodes}

    def _detect_tables(self, bgr: "np.ndarray") -> List[Dict[str, float]]:
        """基于形态学的简易表格区域检测，返回若干大致矩形。"""
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        _, bin_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        # 强化横纵线
        horiz = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1)))
        vert = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40)))
        mask = cv2.add(horiz, vert)
        # 膨胀合并为区域
        mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)), iterations=1)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h, w = gray.shape
        regions: List[Dict[str, float]] = []
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            area = cw * ch
            if area < 0.01 * w * h:  # 过滤极小区域
                continue
            regions.append({"x0": float(x), "y0": float(y), "x1": float(x + cw), "y1": float(y + ch)})
        return regions

    def _detect_red_seals(self, bgr: "np.ndarray") -> List[Dict[str, float]]:
        """基于 HSV 的红章区域检测。"""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        # 红色有两段 Hue 范围
        lower_red1 = np.array([0, 80, 80])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 80, 80])
        upper_red2 = np.array([179, 255, 255])
        mask = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1), cv2.inRange(hsv, lower_red2, upper_red2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)), iterations=1)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h, w, _ = bgr.shape
        regions: List[Dict[str, float]] = []
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            area = cw * ch
            if area < 0.002 * w * h:
                continue
            regions.append({"x0": float(x), "y0": float(y), "x1": float(x + cw), "y1": float(y + ch)})
        return regions

    def _detect_qrcodes(self, bgr: "np.ndarray") -> List[Dict[str, float]]:
        """使用 OpenCV QRCodeDetector 检测二维码位置。"""
        detector = cv2.QRCodeDetector()
        regions: List[Dict[str, float]] = []
        try:
            retval, points = detector.detectMulti(bgr)  # type: ignore[arg-type]
            if retval and points is not None:
                for quad in points:
                    xs = quad[:, 0]
                    ys = quad[:, 1]
                    regions.append(
                        {"x0": float(xs.min()), "y0": float(ys.min()), "x1": float(xs.max()), "y1": float(ys.max())}
                    )
                return regions
        except Exception:
            pass

        try:
            val, points = detector.detect(bgr)
            if val and points is not None:
                xs = points[:, 0, 0]
                ys = points[:, 0, 1]
                regions.append(
                    {"x0": float(xs.min()), "y0": float(ys.min()), "x1": float(xs.max()), "y1": float(ys.max())}
                )
        except Exception:
            return regions
        return regions


__all__ = ["DocumentIngestionService"]
