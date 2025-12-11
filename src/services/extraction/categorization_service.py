"""费用语义分类模块（规则优先，LLM 兜底，不需训练）。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from llm_client import LLMClient

# 业务分类集合，可根据企业需要扩展
CATEGORIES: List[str] = ["差旅", "设备", "办公", "会议", "招待", "科研耗材", "市场营销", "培训", "通讯", "租赁", "其他"]

# 供应商 → 固定类别映射（可后续改为配置或DB）
VENDOR_CATEGORY_MAP: Dict[str, str] = {
    "中国国际航空": "差旅",
    "南方航空": "差旅",
    "东方航空": "差旅",
    "携程": "差旅",
    "滴滴": "差旅",
    "神州专车": "差旅",
    "京东": "设备",
    "阿里云": "设备",
    "华为云": "设备",
    "顺丰": "办公",
    "菜鸟": "办公",
}

# 关键词规则及权重，支持多条命中后累加打分
KEYWORD_RULES: Dict[str, Dict[str, Any]] = {
    "机票": {"category": "差旅", "score": 2},
    "高铁": {"category": "差旅", "score": 2},
    "火车票": {"category": "差旅", "score": 2},
    "打车": {"category": "差旅", "score": 1},
    "出租车": {"category": "差旅", "score": 1},
    "酒店": {"category": "差旅", "score": 2},
    "住宿": {"category": "差旅", "score": 1},
    "会议": {"category": "会议", "score": 2},
    "会务": {"category": "会议", "score": 2},
    "场地费": {"category": "会议", "score": 2},
    "茶歇": {"category": "会议", "score": 1},
    "电脑": {"category": "设备", "score": 2},
    "服务器": {"category": "设备", "score": 2},
    "显示器": {"category": "设备", "score": 2},
    "打印机": {"category": "设备", "score": 2},
    "耗材": {"category": "科研耗材", "score": 2},
    "试剂": {"category": "科研耗材", "score": 2},
    "实验": {"category": "科研耗材", "score": 1},
    "复印纸": {"category": "办公", "score": 1},
    "文具": {"category": "办公", "score": 1},
    "签字笔": {"category": "办公", "score": 1},
    "邮寄": {"category": "办公", "score": 1},
    "电话费": {"category": "通讯", "score": 2},
    "流量": {"category": "通讯", "score": 1},
    "宽带": {"category": "通讯", "score": 2},
    "广告": {"category": "市场营销", "score": 2},
    "投放": {"category": "市场营销", "score": 2},
    "推广": {"category": "市场营销", "score": 2},
    "培训": {"category": "培训", "score": 2},
    "课程": {"category": "培训", "score": 1},
    "租赁": {"category": "租赁", "score": 2},
    "房租": {"category": "租赁", "score": 2},
    "餐饮": {"category": "招待", "score": 2},
    "宴请": {"category": "招待", "score": 2},
    "聚餐": {"category": "招待", "score": 1},
}

# 同义词归一
CATEGORY_SYNONYMS: Dict[str, str] = {
    "差旅费": "差旅",
    "设备费": "设备",
    "办公费": "办公",
    "会议费": "会议",
    "招待费": "招待",
    "科研耗材费": "科研耗材",
}

MAX_DESC_LEN = 256
RULE_SCORE_THRESHOLD = 2  # 规则累计得分达到阈值即可返回


class ExpenseCategorizationService:
    """规则优先、LLM 兜底的费用分类服务，不依赖模型训练。"""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    def categorize(self, schema: Dict[str, Any]) -> str:
        description = self._build_description(schema)

        # 1) 供应商/关键词规则打分
        rule_category = self._rule_based(schema, description)
        if rule_category:
            return rule_category

        # 2) LLM 兜底（严格要求只输出合法类别）
        llm_category = self._llm_categorize(description)
        if llm_category:
            return llm_category

        # 3) 简单关键词兜底
        return self._keyword_baseline(description) or "其他"

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _build_description(self, schema: Dict[str, Any], max_len: int = MAX_DESC_LEN) -> str:
        parts: List[str] = []
        for field in ("notes", "vendor_name"):
            val = schema.get(field)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())
        for item in schema.get("line_items", []) or []:
            desc = item.get("description")
            if isinstance(desc, str) and desc.strip():
                parts.append(desc.strip())
        text = " ".join(parts)
        return text[:max_len] if len(text) > max_len else text

    def _rule_based(self, schema: Dict[str, Any], description: str) -> Optional[str]:
        vendor = (schema.get("vendor_name") or "").strip()
        scores: Dict[str, int] = {}

        # 供应商强规则
        for key, category in VENDOR_CATEGORY_MAP.items():
            if key and key in vendor:
                scores[category] = scores.get(category, 0) + 3  # 强权重

        # 关键词得分
        for keyword, meta in KEYWORD_RULES.items():
            if keyword in description:
                cat = meta["category"]
                scores[cat] = scores.get(cat, 0) + int(meta.get("score", 1))

        if not scores:
            return None
        best_cat, best_score = max(scores.items(), key=lambda kv: kv[1])
        if best_score >= RULE_SCORE_THRESHOLD:
            return best_cat
        return None

    def _llm_categorize(self, description: str) -> Optional[str]:
        if not description:
            return None
        prompt = f"""
你是财务费用分类助手。请根据以下中文描述判断费用类别。
可选类别（只能选一个）：{", ".join(CATEGORIES)}
描述：
{description}
要求：
1. 只输出一个类别名称，例如：差旅 或 设备。
2. 不要输出任何其它文字、标点或解释。
""".strip()
        try:
            reply = self.llm.chat(
                [
                    {"role": "system", "content": "你是严格的费用分类器，只输出合法类别名称。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=16,
            )
        except Exception:
            return None

        reply = (reply or "").strip()
        reply = CATEGORY_SYNONYMS.get(reply, reply)
        if reply in CATEGORIES:
            return reply
        for cat in CATEGORIES:
            if cat in reply:
                return cat
        return None

    def _keyword_baseline(self, text: str) -> Optional[str]:
        for keyword, meta in KEYWORD_RULES.items():
            if keyword in (text or ""):
                return meta["category"]
        return None


__all__ = ["ExpenseCategorizationService"]
