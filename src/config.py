"""全局配置与路径管理。"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
POLICY_DIR = DATA_DIR / "policy"
FEEDBACK_FILE = DATA_DIR / "cache" / "feedback.json"
ANALYTICS_CACHE = DATA_DIR / "cache" / "analytics.json"
DB_PATH = DATA_DIR / "finance.db"

# 确保关键目录存在
for _dir in (DATA_DIR, POLICY_DIR, FEEDBACK_FILE.parent, ANALYTICS_CACHE.parent, DATA_DIR / "input", DATA_DIR / "output"):
    _dir.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    env: str = Field(default=os.getenv("APP_ENV", "dev"))
    debug: bool = Field(default=os.getenv("APP_DEBUG", "true").lower() == "true")

    # LLM / OCR / Embedding 配置
    llm_model: str = Field(default=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    llm_api_key: str = Field(default=os.getenv("DEEPSEEK_API_KEY", ""))
    llm_base_url: str = Field(default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))

    embedding_model: str = Field(default=os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"))
    ocr_endpoints: List[str] = Field(default_factory=lambda: [endpoint.strip() for endpoint in os.getenv("OCR_ENDPOINTS", "").split(",") if endpoint.strip()])
    baidu_app_id: str = Field(default=os.getenv("BAIDU_APP_ID", ""))
    baidu_api_key: str = Field(default=os.getenv("BAIDU_API_KEY", ""))
    baidu_secret_key: str = Field(default=os.getenv("BAIDU_SECRET_KEY", ""))

    # 业务参数
    default_currency: str = Field(default=os.getenv("DEFAULT_CURRENCY", "CNY"))
    duplicate_threshold: float = Field(default=float(os.getenv("DUPLICATE_THRESHOLD", "0.92")))
    anomaly_amount_sigma: float = Field(default=float(os.getenv("ANOMALY_SIGMA", "2.5")))
    anomaly_vendor_history_limit: int = Field(default=int(os.getenv("ANOMALY_VENDOR_HISTORY_LIMIT", "100")))
    anomaly_global_history_limit: int = Field(default=int(os.getenv("ANOMALY_GLOBAL_HISTORY_LIMIT", "500")))
    anomaly_tax_ratio_upper: float = Field(default=float(os.getenv("ANOMALY_TAX_RATIO_UPPER", "0.17")))
    anomaly_tax_ratio_lower: float = Field(default=float(os.getenv("ANOMALY_TAX_RATIO_LOWER", "0.00")))
    anomaly_duplicate_vendor_similarity: float = Field(default=float(os.getenv("ANOMALY_DUP_VENDOR_SIMILARITY", "88.0")))
    anomaly_duplicate_amount_tolerance: float = Field(default=float(os.getenv("ANOMALY_DUP_AMOUNT_TOLERANCE", "0.5")))
    anomaly_duplicate_date_tolerance_days: int = Field(default=int(os.getenv("ANOMALY_DUP_DATE_TOLERANCE_DAYS", "3")))
    anomaly_ml_min_samples: int = Field(default=int(os.getenv("ANOMALY_ML_MIN_SAMPLES", "25")))
    enable_anomaly_ml: bool = Field(default=os.getenv("ENABLE_ANOMALY_ML", "false").lower() == "true")
    analytics_cache_limit: int = Field(default=int(os.getenv("ANALYTICS_CACHE_LIMIT", "5000")))

    # Feature toggles
    enable_policy_rag: bool = Field(default=os.getenv("ENABLE_POLICY_RAG", "true").lower() == "true")
    database_url: str = Field(default=os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}"))

def load_environment() -> None:
    """加载 .env 文件，允许用户在工程根目录放置环境配置。"""
    env_path = ROOT_DIR.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


@lru_cache
def get_settings() -> Settings:
    load_environment()
    return Settings()


__all__ = [
    "ROOT_DIR",
    "DATA_DIR",
    "POLICY_DIR",
    "FEEDBACK_FILE",
    "ANALYTICS_CACHE",
    "DB_PATH",
    "Settings",
    "get_settings",
]
