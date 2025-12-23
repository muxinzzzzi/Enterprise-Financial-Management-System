"""SQLAlchemy ORM 实体。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.schemas import generate_id


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("usr"))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(50), default="owner")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(Text, nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    tax_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="auto_recorded")
    raw_result: Mapped[Dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="documents")
    ledger_entries = relationship("LedgerEntry", back_populates="document", cascade="all, delete-orphan")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("led"))
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    debit_account: Mapped[str] = mapped_column(String(120))
    credit_account: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="ledger_entries")


class AssistantLog(Base):
    __tablename__ = "assistant_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("ast"))
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    context: Mapped[Dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PolicyRule(Base):
    """知识库规则主表。"""

    __tablename__ = "policy_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("rule"))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tags: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    risk_tags: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    scope: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions = relationship("PolicyRuleVersion", back_populates="rule", cascade="all, delete-orphan")


class PolicyRuleVersion(Base):
    """规则版本历史记录。"""

    __tablename__ = "policy_rule_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("rver"))
    rule_id: Mapped[str] = mapped_column(String, ForeignKey("policy_rules.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    risk_tags: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    scope: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rule = relationship("PolicyRule", back_populates="versions")


class ReviewLog(Base):
    """AI 审核修订日志，支持审计追溯。"""

    __tablename__ = "review_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: generate_id("rev"))
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"))
    field_name: Mapped[str] = mapped_column(String(120))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    meta: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    document = relationship("Document")

