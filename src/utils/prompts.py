"""集中存放提示词模板，便于统一维护。"""
from __future__ import annotations

from textwrap import dedent


FIELD_EXTRACTION_PROMPT = dedent(
    """
    你是一名财务票据解析专家。请从给定的OCR文本中抽取结构化字段，输出JSON，字段包括：
    - invoice_number
    - vendor_name
    - tax_id
    - issue_date (ISO格式)
    - currency
    - total_amount
    - tax_amount
    - line_items: 每项包含 description, quantity, unit_price, amount
    - notes
    - unknown_fields: [{"name": str, "value": str}]
    如果没有某个字段，请返回 null。
    OCR 文本："""
)


POLICY_VALIDATION_PROMPT = dedent(
    """
    你需要根据以下规则文档，对票据是否满足条件给出结论。
    规则片段：{rules}
    票据字段：{payload}
    请输出 JSON 数组，每个元素包含: rule_title, severity(LOW/MEDIUM/HIGH), message。
    如果票据符合规则，请返回空数组。
    """
)


NL_QUERY_PROMPT = dedent(
    """
    你是财务分析助手。基于给定的结构化条目，回答用户的问题。
    数据示例：{records}
    用户问题：{question}
    可用字段包含 document_id/vendor/category/currency/amount/tax_amount/issue_date/created_at。
    1. 用中文简洁回答，并引用你使用的字段。
    2. 如果问题涉及筛选/统计，请给出可执行的伪SQL。
    3. 严格输出 JSON（不允许额外解释），schema 为 {"answer": string, "sql": string|null}，无法生成 SQL 时填 null。
    """
)


REPORT_PROMPT = dedent(
    """
    你是财务对账总结机器人。根据票据结果生成审核报告：
    - 总处理数量
    - 按类别统计
    - 金额区间分布
    - 异常/重复/规则违规概要
    - 建议的人工审查重点
    输出 Markdown。
    数据如下：{payload}
    """
)


__all__ = [
    "FIELD_EXTRACTION_PROMPT",
    "NL_QUERY_PROMPT",
    "POLICY_VALIDATION_PROMPT",
    "REPORT_PROMPT",
]
