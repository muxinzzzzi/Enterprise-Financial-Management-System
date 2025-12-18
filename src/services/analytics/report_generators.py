"""报表生成器模块。

实现三类报表的生成：
1. 单张票据审核报告 (Invoice Audit Report)
2. 周期汇总报表 (Period Summary Report)
3. 审计追溯与整改清单 (Audit Trail & Action List)
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from models.schemas import DocumentResult, PolicyFlag
from services.analytics.ai_report_services import DecisionSummaryService, IssueAttributionService


class InvoiceAuditReportGenerator:
    """单张票据审核报告生成器。"""

    def __init__(
        self,
        decision_service: DecisionSummaryService,
        issue_service: IssueAttributionService,
    ) -> None:
        self.decision_service = decision_service
        self.issue_service = issue_service

    def generate(
        self,
        document: DocumentResult,
        policy_flags: List[PolicyFlag],
        anomalies: List[str],
        duplicate_candidates: List[str],
    ) -> str:
        """生成单张票据审核报告的Markdown格式。"""
        # 生成AI结论
        decision_summary = self.decision_service.generate_summary(
            document, policy_flags, anomalies, duplicate_candidates
        )
        issue_classification = self.issue_service.classify_issues(
            document, policy_flags, anomalies, duplicate_candidates
        )

        # 构建Markdown报告
        lines = []
        lines.append("# 单张票据审核报告")
        lines.append("")
        lines.append(f"**报告生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 基本信息
        lines.append("## 一、票据基本信息")
        lines.append("")
        lines.append(f"| 项目 | 内容 |")
        lines.append(f"|------|------|")
        lines.append(f"| 票据ID | {document.document_id} |")
        lines.append(f"| 文件名 | {document.file_name} |")
        lines.append(f"| 供应商 | {document.vendor or 'N/A'} |")
        lines.append(f"| 金额 | {document.total_amount or 0:.2f} {document.currency} |")
        lines.append(f"| 税额 | {document.tax_amount or 0:.2f} {document.currency} |")
        lines.append(f"| 类别 | {document.category or 'N/A'} |")
        lines.append(f"| 开票日期 | {document.issue_date or 'N/A'} |")
        lines.append(f"| OCR置信度 | {document.ocr_confidence:.2%} |")
        lines.append("")

        # 审核结论
        lines.append("## 二、审核结论")
        lines.append("")
        status_emoji = {
            "通过": "✅",
            "需补充": "⚠️",
            "不合规": "❌",
        }
        status = decision_summary.get("status", "需补充")
        risk_level = decision_summary.get("risk_level", "medium")
        lines.append(f"**结论状态：** {status_emoji.get(status, '⚠️')} {status}")
        lines.append(f"**风险等级：** {risk_level.upper()}")
        lines.append("")

        # 关键问题摘要
        summary_points = decision_summary.get("summary_points", [])
        if summary_points:
            lines.append("**关键问题摘要：**")
            lines.append("")
            for i, point in enumerate(summary_points, 1):
                lines.append(f"{i}. {point}")
            lines.append("")
        else:
            lines.append("**关键问题摘要：** 无")
            lines.append("")

        # 证据链
        lines.append("## 三、证据链")
        lines.append("")
        evidence_items = []

        if policy_flags:
            evidence_items.append(f"政策规则校验：发现 {len(policy_flags)} 项问题")
        if anomalies:
            evidence_items.append(f"异常检测：发现 {len(anomalies)} 项异常")
        if duplicate_candidates:
            evidence_items.append(f"重复检测：发现 {len(duplicate_candidates)} 个疑似重复票据")
        if document.ocr_confidence < 0.8:
            evidence_items.append(f"OCR置信度较低：{document.ocr_confidence:.2%}")

        if evidence_items:
            for item in evidence_items:
                lines.append(f"- {item}")
        else:
            lines.append("- 无异常发现")
        lines.append("")

        # 风险点
        lines.append("## 四、风险点")
        lines.append("")
        issue_types = issue_classification.get("issue_types", [])
        severity = issue_classification.get("severity", "medium")
        confidence = issue_classification.get("confidence", 0.5)

        if issue_types:
            lines.append(f"**问题类型：** {', '.join(issue_types)}")
            lines.append(f"**严重程度：** {severity.upper()}")
            lines.append(f"**分类置信度：** {confidence:.2%}")
            lines.append("")
            lines.append("**详细说明：**")
            lines.append("")

            # 政策规则详情
            if policy_flags:
                lines.append("#### 政策规则问题：")
                for flag in policy_flags:
                    severity_emoji = {"LOW": "🟡", "MEDIUM": "🟠", "HIGH": "🔴"}
                    emoji = severity_emoji.get(flag.severity, "🟡")
                    lines.append(f"- {emoji} **{flag.rule_title}** ({flag.severity}): {flag.message}")
                lines.append("")

            # 异常详情
            if anomalies:
                lines.append("#### 异常检测问题：")
                for anomaly in anomalies:
                    lines.append(f"- ⚠️ {anomaly}")
                lines.append("")

            # 重复检测详情
            if duplicate_candidates:
                lines.append("#### 重复检测问题：")
                lines.append(f"- 🔄 发现 {len(duplicate_candidates)} 个疑似重复票据")
                lines.append("")
        else:
            lines.append("无风险点")
            lines.append("")

        # 修改建议
        lines.append("## 五、修改建议")
        lines.append("")
        suggestions = self._generate_suggestions(
            status, issue_types, policy_flags, anomalies, duplicate_candidates
        )
        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(f"{i}. {suggestion}")
        else:
            lines.append("无需修改，审核通过。")
        lines.append("")

        return "\n".join(lines)

    def _generate_suggestions(
        self,
        status: str,
        issue_types: List[str],
        policy_flags: List[PolicyFlag],
        anomalies: List[str],
        duplicate_candidates: List[str],
    ) -> List[str]:
        """生成修改建议。"""
        suggestions = []

        if status == "不合规":
            suggestions.append("此票据存在严重问题，建议拒绝报销或要求重新开具。")

        if "抬头不合规" in issue_types:
            suggestions.append("请检查发票抬头是否符合公司要求，必要时联系供应商修改。")

        if "金额超标准" in issue_types:
            suggestions.append("此金额超过标准限额，请提供额外的审批材料或说明。")

        if "缺少必要材料" in issue_types:
            suggestions.append("请补充必要的审批单、合同或其他支持材料。")

        if "疑似重复报销" in issue_types:
            suggestions.append("疑似重复报销，请核实是否已报销过相同票据。")

        if "日期异常" in issue_types:
            suggestions.append("开票日期异常，请核实日期是否正确。")

        if "税额异常" in issue_types:
            suggestions.append("税额计算异常，请核实税率和税额是否正确。")

        if "OCR识别错误" in issue_types:
            suggestions.append("OCR识别可能存在错误，建议人工核对原始票据。")

        if not suggestions and status == "需补充":
            suggestions.append("请根据上述问题点补充相关材料或说明。")

        return suggestions


class PeriodSummaryReportGenerator:
    """周期汇总报表生成器。"""

    def __init__(
        self,
        decision_service: DecisionSummaryService,
        issue_service: IssueAttributionService,
    ) -> None:
        self.decision_service = decision_service
        self.issue_service = issue_service

    def generate(
        self,
        documents: List[DocumentResult],
        all_policy_flags: Dict[str, List[PolicyFlag]],
        all_anomalies: Dict[str, List[str]],
        all_duplicates: Dict[str, List[str]],
        period_type: str = "月",
        period_label: str = "",
    ) -> str:
        """生成周期汇总报表的Markdown格式。
        
        Args:
            documents: 票据列表
            all_policy_flags: 每个票据ID对应的政策规则列表
            all_anomalies: 每个票据ID对应的异常列表
            all_duplicates: 每个票据ID对应的重复候选列表
            period_type: 周期类型（月/周/项目）
            period_label: 周期标签（如"2025年10期"）
        """
        if not documents:
            return "# 周期汇总报表\n\n**无数据**\n"

        # 统计信息
        stats = self._calculate_statistics(
            documents, all_policy_flags, all_anomalies, all_duplicates
        )

        lines = []
        lines.append("# 周期汇总报表")
        lines.append("")
        lines.append(f"**报表类型：** {period_type}报")
        if period_label:
            lines.append(f"**报表期间：** {period_label}")
        lines.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 本期花费结构
        lines.append("## 一、本期花费结构")
        lines.append("")
        total_amount = stats["total_amount"]
        lines.append(f"**总金额：** {total_amount:.2f} CNY")
        lines.append("")

        # 按类别统计
        category_stats = stats["category_stats"]
        if category_stats:
            lines.append("### 按类别统计")
            lines.append("")
            lines.append("| 类别 | 金额 | 占比 | 票据数 |")
            lines.append("|------|------|------|--------|")
            for category, data in sorted(
                category_stats.items(), key=lambda x: x[1]["amount"], reverse=True
            )[:10]:
                amount = data["amount"]
                count = data["count"]
                percentage = (amount / total_amount * 100) if total_amount > 0 else 0
                lines.append(f"| {category or '未分类'} | {amount:.2f} | {percentage:.1f}% | {count} |")
            lines.append("")

        # 按供应商统计
        vendor_stats = stats["vendor_stats"]
        if vendor_stats:
            lines.append("### 按供应商统计")
            lines.append("")
            lines.append("| 供应商 | 金额 | 票据数 |")
            lines.append("|--------|------|--------|")
            for vendor, data in sorted(
                vendor_stats.items(), key=lambda x: x[1]["amount"], reverse=True
            )[:10]:
                amount = data["amount"]
                count = data["count"]
                lines.append(f"| {vendor or '未知'} | {amount:.2f} | {count} |")
            lines.append("")

        # 合规率
        lines.append("## 二、合规率")
        lines.append("")
        total_count = len(documents)
        passed_count = stats["passed_count"]
        need_supplement_count = stats["need_supplement_count"]
        non_compliant_count = stats["non_compliant_count"]

        compliance_rate = (passed_count / total_count * 100) if total_count > 0 else 0
        lines.append(f"**总票据数：** {total_count}")
        lines.append(f"**通过：** {passed_count} ({passed_count/total_count*100:.1f}%)" if total_count > 0 else "**通过：** 0")
        lines.append(f"**需补充：** {need_supplement_count} ({need_supplement_count/total_count*100:.1f}%)" if total_count > 0 else "**需补充：** 0")
        lines.append(f"**不合规：** {non_compliant_count} ({non_compliant_count/total_count*100:.1f}%)" if total_count > 0 else "**不合规：** 0")
        lines.append(f"**合规率：** {compliance_rate:.1f}%")
        lines.append("")

        # 异常类型分布
        lines.append("## 三、异常类型分布")
        lines.append("")
        issue_distribution = stats["issue_distribution"]
        if issue_distribution:
            lines.append("| 异常类型 | 出现次数 | 占比 |")
            lines.append("|----------|----------|------|")
            total_issues = sum(issue_distribution.values())
            for issue_type, count in sorted(
                issue_distribution.items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / total_issues * 100) if total_issues > 0 else 0
                lines.append(f"| {issue_type} | {count} | {percentage:.1f}% |")
        else:
            lines.append("无异常")
        lines.append("")

        # Top供应商
        lines.append("## 四、Top 供应商")
        lines.append("")
        if vendor_stats:
            top_vendors = sorted(
                vendor_stats.items(), key=lambda x: x[1]["amount"], reverse=True
            )[:5]
            for i, (vendor, data) in enumerate(top_vendors, 1):
                lines.append(f"{i}. **{vendor or '未知'}** - {data['amount']:.2f} CNY ({data['count']} 张票据)")
        else:
            lines.append("无数据")
        lines.append("")

        # Top类别
        lines.append("## 五、Top 类别")
        lines.append("")
        if category_stats:
            top_categories = sorted(
                category_stats.items(), key=lambda x: x[1]["amount"], reverse=True
            )[:5]
            for i, (category, data) in enumerate(top_categories, 1):
                lines.append(f"{i}. **{category or '未分类'}** - {data['amount']:.2f} CNY ({data['count']} 张票据)")
        else:
            lines.append("无数据")
        lines.append("")

        return "\n".join(lines)

    def _calculate_statistics(
        self,
        documents: List[DocumentResult],
        all_policy_flags: Dict[str, List[PolicyFlag]],
        all_anomalies: Dict[str, List[str]],
        all_duplicates: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """计算统计信息。"""
        total_amount = sum(doc.total_amount or 0 for doc in documents)
        category_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"amount": 0.0, "count": 0}
        )
        vendor_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"amount": 0.0, "count": 0}
        )
        issue_distribution: Counter = Counter()
        passed_count = 0
        need_supplement_count = 0
        non_compliant_count = 0

        for doc in documents:
            # 类别统计
            category = doc.category or "未分类"
            category_stats[category]["amount"] += doc.total_amount or 0
            category_stats[category]["count"] += 1

            # 供应商统计
            vendor = doc.vendor or "未知"
            vendor_stats[vendor]["amount"] += doc.total_amount or 0
            vendor_stats[vendor]["count"] += 1

            # 生成决策摘要以统计合规率
            policy_flags = all_policy_flags.get(doc.document_id, [])
            anomalies = all_anomalies.get(doc.document_id, [])
            duplicates = all_duplicates.get(doc.document_id, [])

            decision_summary = self.decision_service.generate_summary(
                doc, policy_flags, anomalies, duplicates
            )
            status = decision_summary.get("status", "需补充")
            if status == "通过":
                passed_count += 1
            elif status == "不合规":
                non_compliant_count += 1
            else:
                need_supplement_count += 1

            # 问题类型分布
            issue_classification = self.issue_service.classify_issues(
                doc, policy_flags, anomalies, duplicates
            )
            for issue_type in issue_classification.get("issue_types", []):
                issue_distribution[issue_type] += 1

        return {
            "total_amount": total_amount,
            "category_stats": dict(category_stats),
            "vendor_stats": dict(vendor_stats),
            "issue_distribution": dict(issue_distribution),
            "passed_count": passed_count,
            "need_supplement_count": need_supplement_count,
            "non_compliant_count": non_compliant_count,
        }


class AuditTrailReportGenerator:
    """审计追溯与整改清单生成器。"""

    def __init__(
        self,
        decision_service: DecisionSummaryService,
        issue_service: IssueAttributionService,
    ) -> None:
        self.decision_service = decision_service
        self.issue_service = issue_service

    def generate(
        self,
        documents: List[DocumentResult],
        all_policy_flags: Dict[str, List[PolicyFlag]],
        all_anomalies: Dict[str, List[str]],
        all_duplicates: Dict[str, List[str]],
    ) -> str:
        """生成审计追溯与整改清单的Markdown格式。"""
        if not documents:
            return "# 审计追溯与整改清单\n\n**无数据**\n"

        # 分类票据
        need_materials = []
        over_standard = []
        suspicious_duplicates = []

        for doc in documents:
            policy_flags = all_policy_flags.get(doc.document_id, [])
            anomalies = all_anomalies.get(doc.document_id, [])
            duplicates = all_duplicates.get(doc.document_id, [])

            issue_classification = self.issue_service.classify_issues(
                doc, policy_flags, anomalies, duplicates
            )
            issue_types = issue_classification.get("issue_types", [])
            severity = issue_classification.get("severity", "medium")

            # 需要补材料
            if "缺少必要材料" in issue_types:
                need_materials.append((doc, issue_classification, severity))

            # 超标准
            if "金额超标准" in issue_types:
                over_standard.append((doc, issue_classification, severity))

            # 疑似重复/异常
            if "疑似重复报销" in issue_types or len(duplicates) > 0:
                suspicious_duplicates.append((doc, issue_classification, severity))

        # 按优先级排序（severity: high > medium > low）
        severity_order = {"high": 3, "medium": 2, "low": 1}

        def sort_key(item: Tuple[DocumentResult, Dict[str, Any], str]) -> Tuple[int, float]:
            doc, classification, severity = item
            priority = severity_order.get(severity, 0)
            amount = doc.total_amount or 0
            return (-priority, -amount)  # 负号用于降序

        need_materials.sort(key=sort_key, reverse=True)
        over_standard.sort(key=sort_key, reverse=True)
        suspicious_duplicates.sort(key=sort_key, reverse=True)

        lines = []
        lines.append("# 审计追溯与整改清单")
        lines.append("")
        lines.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 需要补材料的票据
        lines.append("## 一、需要补材料的票据")
        lines.append("")
        if need_materials:
            lines.append(f"**共 {len(need_materials)} 张票据需要补材料**")
            lines.append("")
            for i, (doc, classification, severity) in enumerate(need_materials, 1):
                lines.append(f"### {i}. {doc.file_name}")
                lines.append("")
                lines.append(f"- **票据ID：** {doc.document_id}")
                lines.append(f"- **供应商：** {doc.vendor or 'N/A'}")
                lines.append(f"- **金额：** {doc.total_amount or 0:.2f} {doc.currency}")
                lines.append(f"- **严重程度：** {severity.upper()}")
                lines.append(f"- **问题类型：** {', '.join(classification.get('issue_types', []))}")
                lines.append("")
        else:
            lines.append("无")
        lines.append("")

        # 超标准的票据
        lines.append("## 二、超标准的票据")
        lines.append("")
        if over_standard:
            lines.append(f"**共 {len(over_standard)} 张票据超标准**")
            lines.append("")
            for i, (doc, classification, severity) in enumerate(over_standard, 1):
                lines.append(f"### {i}. {doc.file_name}")
                lines.append("")
                lines.append(f"- **票据ID：** {doc.document_id}")
                lines.append(f"- **供应商：** {doc.vendor or 'N/A'}")
                lines.append(f"- **金额：** {doc.total_amount or 0:.2f} {doc.currency}")
                lines.append(f"- **严重程度：** {severity.upper()}")
                lines.append(f"- **问题类型：** {', '.join(classification.get('issue_types', []))}")
                lines.append("")
        else:
            lines.append("无")
        lines.append("")

        # 疑似重复/异常的票据
        lines.append("## 三、疑似重复/异常的票据")
        lines.append("")
        if suspicious_duplicates:
            lines.append(f"**共 {len(suspicious_duplicates)} 张票据疑似重复或异常**")
            lines.append("")
            for i, (doc, classification, severity) in enumerate(suspicious_duplicates, 1):
                lines.append(f"### {i}. {doc.file_name}")
                lines.append("")
                lines.append(f"- **票据ID：** {doc.document_id}")
                lines.append(f"- **供应商：** {doc.vendor or 'N/A'}")
                lines.append(f"- **金额：** {doc.total_amount or 0:.2f} {doc.currency}")
                lines.append(f"- **严重程度：** {severity.upper()}")
                lines.append(f"- **问题类型：** {', '.join(classification.get('issue_types', []))}")
                duplicates = all_duplicates.get(doc.document_id, [])
                if duplicates:
                    lines.append(f"- **疑似重复票据ID：** {', '.join(duplicates[:5])}")
                lines.append("")
        else:
            lines.append("无")
        lines.append("")

        # 汇总统计
        lines.append("## 四、汇总统计")
        lines.append("")
        total_issues = len(need_materials) + len(over_standard) + len(suspicious_duplicates)
        lines.append(f"**需要整改的票据总数：** {total_issues}")
        lines.append(f"- 需要补材料：{len(need_materials)}")
        lines.append(f"- 超标准：{len(over_standard)}")
        lines.append(f"- 疑似重复/异常：{len(suspicious_duplicates)}")
        lines.append("")

        return "\n".join(lines)


__all__ = [
    "InvoiceAuditReportGenerator",
    "PeriodSummaryReportGenerator",
    "AuditTrailReportGenerator",
]
