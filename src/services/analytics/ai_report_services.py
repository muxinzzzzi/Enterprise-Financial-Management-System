"""报表生成模块中的 AI 关键点服务。

本模块实现两个核心 AI 关键点：
- AI 关键点 A：审核结论自动生成（Decision Summary）
- AI 关键点 B：问题归因与类型化（Issue Attribution & Taxonomy）
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from llm_client import LLMClient
from models.schemas import DocumentResult, PolicyFlag

logger = logging.getLogger(__name__)


class DecisionSummaryService:
    """AI 关键点 A：审核结论自动生成服务。
    
    基于结构化字段、规则校验结果与异常检测结果，自动生成每张发票的审核结论摘要。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    def generate_summary(
        self,
        document: DocumentResult,
        policy_flags: List[PolicyFlag],
        anomalies: List[str],
        duplicate_candidates: List[str],
    ) -> Dict[str, Any]:
        """生成审核结论摘要。
        
        Args:
            document: 票据结果
            policy_flags: 政策规则校验结果
            anomalies: 异常检测结果
            duplicate_candidates: 重复候选列表
            
        Returns:
            包含 status, summary_points, risk_level 的字典
        """
        # 构建输入数据
        payload = {
            "document_id": document.document_id,
            "file_name": document.file_name,
            "vendor": document.vendor,
            "amount": document.total_amount,
            "tax_amount": document.tax_amount,
            "category": document.category,
            "issue_date": document.issue_date,
            "policy_flags": [
                {
                    "rule_title": flag.rule_title,
                    "severity": flag.severity,
                    "message": flag.message,
                }
                for flag in policy_flags
            ],
            "anomalies": anomalies,
            "duplicate_candidates": duplicate_candidates,
            "ocr_confidence": document.ocr_confidence,
        }

        prompt = self._build_prompt(payload)

        try:
            response = self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": "你是财务审核专家，负责生成票据审核结论。请严格输出JSON格式，包含status、summary_points、risk_level三个字段。",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            result = json.loads(response)
            # 验证并规范化结果
            return self._normalize_result(result)
        except json.JSONDecodeError as e:
            logger.warning(f"LLM返回非JSON格式，使用回退逻辑: {e}")
            return self._fallback_summary(policy_flags, anomalies, duplicate_candidates)
        except Exception as e:
            logger.exception(f"生成审核结论失败: {e}")
            return self._fallback_summary(policy_flags, anomalies, duplicate_candidates)

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        """构建提示词。"""
        return f"""
请基于以下票据数据生成审核结论：

**票据信息：**
- 文件名：{payload.get('file_name', 'N/A')}
- 供应商：{payload.get('vendor', 'N/A')}
- 金额：{payload.get('amount', 0):.2f}
- 税额：{payload.get('tax_amount', 0):.2f}
- 类别：{payload.get('category', 'N/A')}
- 开票日期：{payload.get('issue_date', 'N/A')}
- OCR置信度：{payload.get('ocr_confidence', 0):.2f}

**政策规则校验结果：**
{json.dumps(payload.get('policy_flags', []), ensure_ascii=False, indent=2)}

**异常检测结果：**
{json.dumps(payload.get('anomalies', []), ensure_ascii=False)}

**重复检测结果：**
{len(payload.get('duplicate_candidates', []))} 个疑似重复票据

**要求：**
1. 综合分析上述信息，生成审核结论
2. status 字段：取值为 "通过"、"需补充"、"不合规" 之一
3. summary_points 字段：关键问题摘要列表（3-5条，每条不超过50字）
4. risk_level 字段：风险等级，取值为 "low"、"medium"、"high" 之一

**输出格式（严格JSON）：**
{{
  "status": "通过|需补充|不合规",
  "summary_points": ["问题1", "问题2", ...],
  "risk_level": "low|medium|high"
}}
"""

    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """规范化LLM返回的结果。"""
        status = result.get("status", "需补充")
        if status not in ["通过", "需补充", "不合规"]:
            status = "需补充"

        summary_points = result.get("summary_points", [])
        if not isinstance(summary_points, list):
            summary_points = []

        risk_level = result.get("risk_level", "medium")
        if risk_level not in ["low", "medium", "high"]:
            risk_level = "medium"

        return {
            "status": status,
            "summary_points": summary_points[:5],  # 最多5条
            "risk_level": risk_level,
        }

    def _fallback_summary(
        self,
        policy_flags: List[PolicyFlag],
        anomalies: List[str],
        duplicate_candidates: List[str],
    ) -> Dict[str, Any]:
        """回退逻辑：基于规则判断生成简单结论。"""
        has_high_severity = any(flag.severity == "HIGH" for flag in policy_flags)
        has_anomalies = len(anomalies) > 0
        has_duplicates = len(duplicate_candidates) > 0

        if has_high_severity:
            status = "不合规"
            risk_level = "high"
        elif has_anomalies or has_duplicates or len(policy_flags) > 0:
            status = "需补充"
            risk_level = "medium"
        else:
            status = "通过"
            risk_level = "low"

        summary_points = []
        if has_high_severity:
            summary_points.append("存在高风险政策违规")
        if has_anomalies:
            summary_points.append(f"检测到{len(anomalies)}项异常")
        if has_duplicates:
            summary_points.append("疑似重复报销")
        if len(policy_flags) > 0:
            summary_points.append(f"{len(policy_flags)}项政策提醒")

        return {
            "status": status,
            "summary_points": summary_points or ["审核通过"],
            "risk_level": risk_level,
        }


class IssueAttributionService:
    """AI 关键点 B：问题归因与类型化服务。
    
    将票据存在的问题自动归类到统一的问题体系（taxonomy），支持统计与对比分析。
    """

    # 预定义问题类型体系
    ISSUE_TAXONOMY = [
        "抬头不合规",
        "金额超标准",
        "缺少必要材料",
        "类别疑似错误",
        "疑似重复报销",
        "日期异常",
        "税额异常",
        "OCR识别错误",
        "政策规则冲突",
        "其他异常",
    ]

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    def classify_issues(
        self,
        document: DocumentResult,
        policy_flags: List[PolicyFlag],
        anomalies: List[str],
        duplicate_candidates: List[str],
    ) -> Dict[str, Any]:
        """对问题进行归因和类型化。
        
        Args:
            document: 票据结果
            policy_flags: 政策规则校验结果
            anomalies: 异常检测结果
            duplicate_candidates: 重复候选列表
            
        Returns:
            包含 issue_types, severity, confidence 的字典
        """
        # 构建输入数据
        payload = {
            "document_id": document.document_id,
            "file_name": document.file_name,
            "vendor": document.vendor,
            "amount": document.total_amount,
            "category": document.category,
            "policy_flags": [
                {
                    "rule_title": flag.rule_title,
                    "severity": flag.severity,
                    "message": flag.message,
                }
                for flag in policy_flags
            ],
            "anomalies": anomalies,
            "duplicate_candidates": duplicate_candidates,
        }

        prompt = self._build_prompt(payload)

        try:
            response = self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": "你是财务问题分析专家，负责将票据问题归类到统一的问题体系。请严格输出JSON格式。",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=600,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            result = json.loads(response)
            return self._normalize_classification(result)
        except json.JSONDecodeError as e:
            logger.warning(f"LLM返回非JSON格式，使用规则匹配: {e}")
            return self._rule_based_classification(policy_flags, anomalies, duplicate_candidates)
        except Exception as e:
            logger.exception(f"问题归因失败: {e}")
            return self._rule_based_classification(policy_flags, anomalies, duplicate_candidates)

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        """构建提示词。"""
        taxonomy_str = "\n".join(f"- {issue}" for issue in self.ISSUE_TAXONOMY)

        return f"""
请将以下票据的问题归类到预定义的问题体系：

**票据信息：**
- 文件名：{payload.get('file_name', 'N/A')}
- 供应商：{payload.get('vendor', 'N/A')}
- 金额：{payload.get('amount', 0):.2f}
- 类别：{payload.get('category', 'N/A')}

**政策规则校验结果：**
{json.dumps(payload.get('policy_flags', []), ensure_ascii=False, indent=2)}

**异常检测结果：**
{json.dumps(payload.get('anomalies', []), ensure_ascii=False)}

**重复检测结果：**
{len(payload.get('duplicate_candidates', []))} 个疑似重复票据

**预定义问题类型体系：**
{taxonomy_str}

**要求：**
1. 分析上述问题，将其映射到预定义的问题类型
2. issue_types 字段：问题类型列表（从预定义体系中选择，可多选）
3. severity 字段：整体严重程度，取值为 "low"、"medium"、"high" 之一
4. confidence 字段：分类置信度，0.0-1.0之间的浮点数

**输出格式（严格JSON）：**
{{
  "issue_types": ["问题类型1", "问题类型2", ...],
  "severity": "low|medium|high",
  "confidence": 0.85
}}
"""

    def _normalize_classification(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """规范化分类结果。"""
        issue_types = result.get("issue_types", [])
        if not isinstance(issue_types, list):
            issue_types = []

        # 过滤掉不在预定义体系中的类型
        valid_types = [t for t in issue_types if t in self.ISSUE_TAXONOMY]
        if not valid_types:
            valid_types = ["其他异常"]

        severity = result.get("severity", "medium")
        if severity not in ["low", "medium", "high"]:
            severity = "medium"

        confidence = result.get("confidence", 0.5)
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.5

        return {
            "issue_types": valid_types,
            "severity": severity,
            "confidence": confidence,
        }

    def _rule_based_classification(
        self,
        policy_flags: List[PolicyFlag],
        anomalies: List[str],
        duplicate_candidates: List[str],
    ) -> Dict[str, Any]:
        """基于规则的分类（回退逻辑）。"""
        issue_types = []
        severity = "low"
        confidence = 0.7

        # 检查重复
        if len(duplicate_candidates) > 0:
            issue_types.append("疑似重复报销")
            severity = "high"
            confidence = 0.9

        # 检查政策规则
        for flag in policy_flags:
            message_lower = flag.message.lower()
            if "抬头" in flag.message or "抬头" in flag.rule_title:
                if "抬头不合规" not in issue_types:
                    issue_types.append("抬头不合规")
            if "金额" in flag.message or "超标准" in flag.message or "标准" in flag.message:
                if "金额超标准" not in issue_types:
                    issue_types.append("金额超标准")
            if "材料" in flag.message or "审批" in flag.message:
                if "缺少必要材料" not in issue_types:
                    issue_types.append("缺少必要材料")

            if flag.severity == "HIGH":
                severity = "high"
            elif flag.severity == "MEDIUM" and severity != "high":
                severity = "medium"

        # 检查异常
        for anomaly in anomalies:
            anomaly_lower = anomaly.lower()
            if "日期" in anomaly or "跨年" in anomaly:
                if "日期异常" not in issue_types:
                    issue_types.append("日期异常")
            if "税额" in anomaly or "税率" in anomaly:
                if "税额异常" not in issue_types:
                    issue_types.append("税额异常")
            if "ocr" in anomaly_lower or "识别" in anomaly:
                if "OCR识别错误" not in issue_types:
                    issue_types.append("OCR识别错误")

        if not issue_types:
            issue_types = ["其他异常"]
            confidence = 0.5

        return {
            "issue_types": issue_types,
            "severity": severity,
            "confidence": confidence,
        }


__all__ = ["DecisionSummaryService", "IssueAttributionService"]
