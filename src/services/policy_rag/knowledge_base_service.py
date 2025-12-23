"""知识库规则管理服务：增删改查 + 版本控制 + RAG 同步。"""
from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Dict, List, Tuple

from pathlib import Path
from database import db_session
from llm_client import LLMClient
from models.db_models import PolicyRule, PolicyRuleVersion
from models.schemas import KnowledgeRulePayload, PolicyDocument

from .rule_summarizer import RuleSummarizer
from .policy_service import PolicyValidationService


def _now() -> datetime:
    return datetime.utcnow()


class KnowledgeBaseService:
    def __init__(self, llm: LLMClient, policy_service: PolicyValidationService) -> None:
        self.summarizer = RuleSummarizer(llm)
        self.policy_service = policy_service
        self.shadow_path = Path(__file__).with_name("shadow_rules.json")

    # ------------- 查询接口 -------------
    def list_rules(
        self,
        q: str | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        page = max(1, page)
        page_size = max(1, min(50, page_size))
        with db_session() as session:
            query = session.query(PolicyRule).filter(PolicyRule.status != "deleted")
            if q:
                like = f"%{q}%"
                query = query.filter((PolicyRule.title.ilike(like)) | (PolicyRule.content.ilike(like)))
            if category:
                query = query.filter(PolicyRule.category == category)
            total = query.count()
            rules = (
                query.order_by(PolicyRule.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            return {
                "items": [self._to_dict(rule) for rule in rules],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    def get_rule(self, rule_id: str) -> Dict[str, Any] | None:
        with db_session() as session:
            rule = session.query(PolicyRule).filter(PolicyRule.id == rule_id).first()
            return self._to_dict(rule) if rule else None

    def list_versions(self, rule_id: str) -> List[Dict[str, Any]]:
        with db_session() as session:
            versions = (
                session.query(PolicyRuleVersion)
                .filter(PolicyRuleVersion.rule_id == rule_id)
                .order_by(PolicyRuleVersion.version.desc())
                .all()
            )
            return [
                {
                    "id": v.id,
                    "rule_id": v.rule_id,
                    "version": v.version,
                    "title": v.title,
                    "summary": v.summary,
                    "category": v.category,
                    "risk_tags": self._dict_to_list(v.risk_tags),
                    "scope": self._dict_to_list(v.scope),
                    "change_note": v.change_note,
                    "created_by": v.created_by,
                    "created_at": v.created_at.isoformat(),
                }
                for v in versions
            ]

    # ------------- 写入接口 -------------
    def create_rule(self, payload: KnowledgeRulePayload, user_id: str | None = None) -> Dict[str, Any]:
        summary, tags, risk_tags, scope = self._prepare_rule(payload)
        with db_session() as session:
            rule = PolicyRule(
                title=payload.title,
                content=payload.content,
                summary=summary,
                category=payload.category,
                tags=tags,
                risk_tags=risk_tags,
                scope=scope,
                status="active",
                version=1,
                created_by=user_id,
                updated_by=user_id,
                created_at=_now(),
                updated_at=_now(),
            )
            session.add(rule)
            session.flush()  # 确保拿到 rule.id

            version = PolicyRuleVersion(
                rule_id=rule.id,
                version=1,
                title=rule.title,
                content=rule.content,
                summary=rule.summary,
                category=rule.category,
                risk_tags=rule.risk_tags,
                scope=rule.scope,
                change_note=payload.change_note or "创建",
                created_by=user_id,
                created_at=_now(),
            )
            session.add(version)
        # 同步向量索引
        self.refresh_vector_store()
        self._append_shadow_rule(rule)
        return self.get_rule(rule.id) or {}

    def update_rule(self, rule_id: str, payload: KnowledgeRulePayload, user_id: str | None = None) -> Dict[str, Any]:
        with db_session() as session:
            rule = session.query(PolicyRule).filter(PolicyRule.id == rule_id, PolicyRule.status != "deleted").first()
            if not rule:
                raise ValueError("规则不存在或已删除")

            summary, tags, risk_tags, scope = self._prepare_rule(payload)
            rule.title = payload.title
            rule.content = payload.content
            rule.summary = summary
            rule.category = payload.category
            rule.tags = tags
            rule.risk_tags = risk_tags
            rule.scope = scope
            rule.updated_by = user_id
            rule.updated_at = _now()
            rule.version = (rule.version or 1) + 1

            version = PolicyRuleVersion(
                rule_id=rule.id,
                version=rule.version,
                title=rule.title,
                content=rule.content,
                summary=rule.summary,
                category=rule.category,
                risk_tags=rule.risk_tags,
                scope=rule.scope,
                change_note=payload.change_note or "更新",
                created_by=user_id,
                created_at=_now(),
            )
            session.add(version)
        self.refresh_vector_store()
        return self.get_rule(rule_id) or {}

    def refresh_vector_store(self) -> Dict[str, Any]:
        """将知识库规则同步到向量索引，同时加入影子规则；跳过 LLM 摘要，直接用已有 summary。"""
        texts: List[str] = []
        metas: List[dict] = []

        with db_session() as session:
            rules = session.query(PolicyRule).filter(PolicyRule.status == "active").all()
            for r in rules:
                summary = r.summary or r.content
                texts.append(summary)
                metas.append(
                    {
                        "title": r.title,
                        "content": r.content,
                        "summary": summary,
                        "description": summary,
                        "source": "policy",
                        **(r.tags or {}),
                        "risk_tags": r.risk_tags or {},
                        "scope": r.scope or {},
                    }
                )

        # 加入 shadow_rules.json
        if self.shadow_path.exists():
            try:
                data = json.loads(self.shadow_path.read_text(encoding="utf-8"))
                for item in data if isinstance(data, list) else []:
                    summary = item.get("summary") or item.get("content") or ""
                    content = item.get("content") or summary
                    texts.append(summary)
                    metas.append(
                        {
                            "title": item.get("title", "shadow_rule"),
                            "content": content,
                            "summary": summary,
                            "description": summary,
                            "source": "shadow_rule",
                            "expense_type": item.get("expense_type") or [],
                            "scene": item.get("scene") or [],
                            "city_level": item.get("city_level") or "",
                        }
                    )
            except Exception:
                pass

        self.policy_service.store.clear()
        if texts:
            self.policy_service.store.add_texts(texts, metas)
        return {"count": len(texts)}

    def delete_rules(self, ids: List[str]) -> Dict[str, Any]:
        if not ids:
            return {"deleted": 0}
        deleted = 0
        with db_session() as session:
            rules = session.query(PolicyRule).filter(PolicyRule.id.in_(ids)).all()
            for r in rules:
                r.status = "deleted"
                r.updated_at = _now()
                session.add(r)
                deleted += 1
        if deleted:
            self.refresh_vector_store()
        return {"deleted": deleted}

    def seed_shadow_rules(self) -> Dict[str, Any]:
        """读取 shadow_rules.json，将不存在的规则写入数据库。"""
        if not self.shadow_path.exists():
            return {"imported": 0}
        data = []
        try:
            data = json.loads(self.shadow_path.read_text(encoding="utf-8"))
        except Exception:
            return {"imported": 0}
        imported = 0
        with db_session() as session:
            for item in data if isinstance(data, list) else []:
                title = item.get("title")
                content = item.get("content") or item.get("summary") or ""
                if not title or not content:
                    continue
                exists = (
                    session.query(PolicyRule)
                    .filter((PolicyRule.id == item.get("id")) | (PolicyRule.title == title))
                    .first()
                )
                if exists:
                    continue
                payload = KnowledgeRulePayload(
                    title=title,
                    content=content,
                    summary=item.get("summary"),
                    category=(item.get("expense_type") or [""])[0] if isinstance(item.get("expense_type"), list) else item.get("expense_type"),
                    tags=item.get("expense_type") or [],
                    risk_tags=item.get("risk_tags") or [],
                    scope=item.get("scene") or [],
                    change_note="导入影子规则",
                )
                summary, tags, risk_tags, scope = self._prepare_rule(payload)
                rule = PolicyRule(
                    id=item.get("id") or None,
                    title=payload.title,
                    content=payload.content,
                    summary=summary,
                    category=payload.category,
                    tags=tags,
                    risk_tags=risk_tags,
                    scope=scope,
                    status="active",
                    version=1,
                    created_by="shadow_seed",
                    updated_by="shadow_seed",
                    created_at=_now(),
                    updated_at=_now(),
                )
                session.add(rule)
                session.flush()
                version = PolicyRuleVersion(
                    rule_id=rule.id,
                    version=1,
                    title=rule.title,
                    content=rule.content,
                    summary=rule.summary,
                    category=rule.category,
                    risk_tags=rule.risk_tags,
                    scope=rule.scope,
                    change_note="导入影子规则",
                    created_by="shadow_seed",
                    created_at=_now(),
                )
                session.add(version)
                imported += 1
        if imported:
            self.refresh_vector_store()
        return {"imported": imported}

    # ------------- 辅助方法 -------------
    def _prepare_rule(self, payload: KnowledgeRulePayload) -> Tuple[str, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """生成摘要并规范化标签字段。"""
        policy_doc = PolicyDocument(title=payload.title, content=payload.content)
        summary = payload.summary or self.summarizer.summarize(policy_doc)
        tags = {"items": payload.tags} if payload.tags else {}
        risk_tags = {"items": payload.risk_tags} if payload.risk_tags else {}
        scope = {"items": payload.scope} if payload.scope else {}
        return summary, tags, risk_tags, scope

    def _to_dict(self, rule: PolicyRule | None) -> Dict[str, Any]:
        if not rule:
            return {}
        return {
            "id": rule.id,
            "title": rule.title,
            "summary": rule.summary,
            "content": rule.content,
            "category": rule.category,
            "tags": self._dict_to_list(rule.tags),
            "risk_tags": self._dict_to_list(rule.risk_tags),
            "scope": self._dict_to_list(rule.scope),
            "status": rule.status,
            "version": rule.version,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            "created_by": rule.created_by,
            "updated_by": rule.updated_by,
        }

    @staticmethod
    def _dict_to_list(data: Dict[str, Any] | None) -> List[str]:
        if not data:
            return []
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            return [str(x) for x in data["items"]]
        if isinstance(data, list):
            return [str(x) for x in data]
        return []

    def _append_shadow_rule(self, rule: PolicyRule) -> None:
        """追加规则到 shadow_rules.json，保持模板字段。"""
        if not self.shadow_path:
            return
        try:
            payload = []
            if self.shadow_path.exists():
                payload = json.loads(self.shadow_path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                payload = []
            tag_items = []
            if isinstance(rule.tags, dict) and isinstance(rule.tags.get("items"), list):
                tag_items = rule.tags["items"]
            risk_items = []
            if isinstance(rule.risk_tags, dict) and isinstance(rule.risk_tags.get("items"), list):
                risk_items = rule.risk_tags["items"]
            scope_items = []
            if isinstance(rule.scope, dict) and isinstance(rule.scope.get("items"), list):
                scope_items = rule.scope["items"]
            payload.append(
                {
                    "id": rule.id,
                    "title": rule.title,
                    "summary": rule.summary,
                    "content": rule.content,
                    "expense_type": tag_items,
                    "scene": scope_items,
                    "org_scope": [],
                    "funding_scope": [],
                    "risk_tags": risk_items,
                    "severity_default": "MEDIUM",
                }
            )
            self.shadow_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


__all__ = ["KnowledgeBaseService"]


