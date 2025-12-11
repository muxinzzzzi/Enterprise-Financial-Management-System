"""异常检测与重复报销识别。"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, median, pstdev
from typing import Any, Callable, Deque, Dict, List, Optional

import numpy as np
from rapidfuzz import fuzz

from config import get_settings

try:  # 可选依赖，未安装时自动降级
    from sklearn.ensemble import IsolationForest
except Exception:  # pragma: no cover - 兼容运行时环境
    IsolationForest = None


@dataclass
class ReceiptProfile:
    document_id: str
    vendor: str
    normalized_vendor: str
    issue_date: Optional[datetime]
    amount: Optional[float]
    tax_amount: Optional[float]
    category: Optional[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RuleDefinition:
    name: str
    message: str
    predicate: Callable[[ReceiptProfile, Dict[str, Any]], bool]


class AnomalyDetectionService:
    """包含模糊重复检测 + 多层级异常识别的服务。"""

    DUPLICATE_BUFFER_LIMIT = 2000

    def __init__(self) -> None:
        self.settings = get_settings()
        self.global_amount_history: Deque[float] = deque(maxlen=self.settings.anomaly_global_history_limit)
        self.vendor_amount_history: Dict[str, Deque[float]] = {}
        self.duplicate_profiles: Deque[ReceiptProfile] = deque(maxlen=self.DUPLICATE_BUFFER_LIMIT)
        self.rules = self._build_rules()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def analyze(self, document_id: str, normalized: Dict[str, Any]) -> Dict[str, List[str]]:
        profile = self._build_profile(document_id, normalized)
        duplicates = self._detect_duplicates(profile)
        anomalies = []
        anomalies.extend(self._run_amount_analyzers(profile))
        anomalies.extend(self._evaluate_rules(profile, normalized))
        return {"anomalies": anomalies, "duplicates": duplicates}

    # ------------------------------------------------------------------ #
    # Duplicate detection
    # ------------------------------------------------------------------ #
    def _detect_duplicates(self, profile: ReceiptProfile) -> List[str]:
        if not profile.amount:
            self._remember_profile(profile)
            return []

        matches: List[str] = []
        for candidate in self.duplicate_profiles:
            if candidate.document_id == profile.document_id:
                continue
            if self._is_duplicate(profile, candidate):
                matches.append(candidate.document_id)
        self._remember_profile(profile)
        return matches

    def _remember_profile(self, profile: ReceiptProfile) -> None:
        self.duplicate_profiles.append(profile)

    def _is_duplicate(self, current: ReceiptProfile, candidate: ReceiptProfile) -> bool:
        similarity = fuzz.token_set_ratio(current.normalized_vendor, candidate.normalized_vendor)
        if similarity < self.settings.anomaly_duplicate_vendor_similarity:
            return False

        if not self._is_value_close(current.amount, candidate.amount, self.settings.anomaly_duplicate_amount_tolerance):
            return False

        if not self._date_within(current.issue_date, candidate.issue_date, self.settings.anomaly_duplicate_date_tolerance_days):
            return False

        if current.tax_amount is not None and candidate.tax_amount is not None:
            if not self._is_value_close(current.tax_amount, candidate.tax_amount, 0.5):
                return False

        return True

    @staticmethod
    def _is_value_close(a: Optional[float], b: Optional[float], tolerance: float) -> bool:
        if a is None or b is None:
            return False
        return abs(a - b) <= tolerance

    @staticmethod
    def _date_within(a: Optional[datetime], b: Optional[datetime], days: int) -> bool:
        if not a or not b:
            return True  # 缺失日期时保持放行，仅凭金额/供应商判断
        return abs((a - b).days) <= days

    # ------------------------------------------------------------------ #
    # Amount anomaly detection
    # ------------------------------------------------------------------ #
    def _run_amount_analyzers(self, profile: ReceiptProfile) -> List[str]:
        amount = profile.amount
        if amount is None:
            return []

        vendor_key = profile.normalized_vendor or "unknown"
        vendor_history = self.vendor_amount_history.setdefault(
            vendor_key, deque(maxlen=self.settings.anomaly_vendor_history_limit)
        )
        previous_vendor_values = list(vendor_history)
        previous_global_values = list(self.global_amount_history)

        vendor_history.append(amount)
        self.global_amount_history.append(amount)

        findings: List[str] = []
        findings.extend(self._z_score_alert(previous_vendor_values, amount, f"供应商「{profile.vendor}」"))
        findings.extend(self._z_score_alert(previous_global_values, amount, "全局"))
        findings.extend(self._mad_alert(previous_vendor_values, amount, profile.vendor))

        ml_alert = self._isolation_forest_alert(previous_vendor_values, amount, profile.vendor)
        if ml_alert:
            findings.append(ml_alert)

        return findings

    def _z_score_alert(self, history: List[float], value: float, scope: str) -> List[str]:
        if len(history) < 5:
            return []
        mu = mean(history)
        sigma = pstdev(history) or 1.0
        z = abs(value - mu) / sigma
        if z > self.settings.anomaly_amount_sigma:
            return [f"{scope}金额达到 {z:.2f}σ，建议人工复核"]
        return []

    def _mad_alert(self, history: List[float], value: float, vendor: str | None) -> List[str]:
        if len(history) < 8:
            return []
        med = median(history)
        deviations = [abs(x - med) for x in history]
        mad = median(deviations) or 1.0
        score = abs(value - med) / (1.4826 * mad)
        if score > 3.5:
            label = vendor or "未知供应商"
            return [f"供应商「{label}」金额偏离历史中位数 (MAD={score:.2f})"]
        return []

    def _isolation_forest_alert(self, history: List[float], value: float, vendor: str | None) -> Optional[str]:
        if not self.settings.enable_anomaly_ml or IsolationForest is None:
            return None
        if len(history) < self.settings.anomaly_ml_min_samples:
            return None
        model = IsolationForest(contamination=0.03, random_state=42)
        model.fit(np.array(history).reshape(-1, 1))
        score = model.decision_function([[value]])[0]
        if score < -0.1:
            label = vendor or "未知供应商"
            return f"IsolationForest 判定供应商「{label}」金额异常 (score={score:.2f})"
        return None

    # ------------------------------------------------------------------ #
    # Rule engine
    # ------------------------------------------------------------------ #
    def _build_rules(self) -> List[RuleDefinition]:
        upper = self.settings.anomaly_tax_ratio_upper
        lower = self.settings.anomaly_tax_ratio_lower
        return [
            RuleDefinition(
                name="tax_gt_total",
                message="税额大于总额，疑似 OCR 解析错误",
                predicate=lambda profile, _: profile.tax_amount is not None
                and profile.amount is not None
                and profile.tax_amount > profile.amount,
            ),
            RuleDefinition(
                name="tax_ratio_high",
                message=f"税率超过 {upper * 100:.1f}% ，请核对税目",
                predicate=lambda profile, _: self._tax_ratio(profile) is not None and self._tax_ratio(profile) > upper,
            ),
            RuleDefinition(
                name="tax_ratio_low",
                message=f"税率低于 {lower * 100:.1f}% ，与常规增值税不符",
                predicate=lambda profile, _: profile.amount
                and profile.amount > 200
                and self._tax_ratio(profile) is not None
                and self._tax_ratio(profile) < lower,
            ),
            RuleDefinition(
                name="high_meal_expense",
                message="餐饮类别单笔超 2000 元，可能需要审批凭证",
                predicate=lambda profile, payload: self._category_contains(profile, payload, ("餐", "meal"))
                and profile.amount is not None
                and profile.amount > 2000,
            ),
        ]

    def _evaluate_rules(self, profile: ReceiptProfile, normalized: Dict[str, Any]) -> List[str]:
        findings: List[str] = []
        for rule in self.rules:
            try:
                if rule.predicate(profile, normalized):
                    findings.append(rule.message)
            except Exception:
                continue
        return findings

    # ------------------------------------------------------------------ #
    # Profile helpers
    # ------------------------------------------------------------------ #
    def _build_profile(self, document_id: str, normalized: Dict[str, Any]) -> ReceiptProfile:
        vendor = (normalized.get("vendor_name") or "未知供应商").strip()
        normalized_vendor = self._normalize_vendor(vendor)
        issue_date = self._parse_date(normalized.get("issue_date"))
        amount = self._to_float(normalized.get("total_amount"))
        tax_amount = self._to_float(normalized.get("tax_amount"))
        category = normalized.get("category") or normalized.get("expense_category")
        return ReceiptProfile(
            document_id=document_id,
            vendor=vendor,
            normalized_vendor=normalized_vendor,
            issue_date=issue_date,
            amount=amount,
            tax_amount=tax_amount,
            category=category,
        )

    @staticmethod
    def _normalize_vendor(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        candidates = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d",
        ]
        for fmt in candidates:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
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
        if not sanitized:
            return None
        sanitized = sanitized.replace("(", "-").replace(")", "")
        sanitized = sanitized.replace("（", "-").replace("）", "")
        try:
            return float(sanitized)
        except ValueError:
            return None

    @staticmethod
    def _tax_ratio(profile: ReceiptProfile) -> Optional[float]:
        if profile.amount is None or profile.amount == 0 or profile.tax_amount is None:
            return None
        return profile.tax_amount / profile.amount

    @staticmethod
    def _category_contains(profile: ReceiptProfile, payload: Dict[str, Any], keywords: tuple[str, ...]) -> bool:
        category = (profile.category or payload.get("category") or "").lower()
        return any(keyword.lower() in category for keyword in keywords)


__all__ = ["AnomalyDetectionService"]
