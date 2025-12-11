"""用户登录/注册逻辑。"""
from __future__ import annotations

from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from database import db_session
from models.db_models import User
from models.schemas import generate_id


def create_user(name: str, email: str, password: str, role: str = "owner") -> User:
    password_hash = generate_password_hash(password)
    with db_session() as session:
        user = session.query(User).filter_by(email=email).first()
        if user:
            user.name = name
            user.role = role
            user.password_hash = password_hash
            session.flush()
            return user
        user = User(
            id=generate_id("usr"),
            name=name,
            email=email,
            role=role,
            password_hash=password_hash,
        )
        session.add(user)
        session.flush()
        return user


def ensure_user(name: str, email: str, password: str = "123456", role: str = "owner") -> User:
    with db_session() as session:
        user = session.query(User).filter_by(email=email).first()
        if user:
            return user
        user = User(
            id=generate_id("usr"),
            name=name,
            email=email,
            role=role,
            password_hash=generate_password_hash(password),
        )
        session.add(user)
        session.flush()
        return user


def authenticate(email: str, password: str) -> Optional[User]:
    with db_session() as session:
        user = session.query(User).filter_by(email=email).first()
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            return user
        return None


def login_or_register(name: str, email: str, role: str = "owner") -> User:
    """兼容旧流程：无密码时使用默认密码。"""
    return ensure_user(name=name, email=email, role=role)


def list_users() -> list[dict]:
    with db_session() as session:
        users = session.query(User).all()
        return [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ]


def get_user(user_id: str) -> Optional[User]:
    with db_session() as session:
        return session.get(User, user_id)


__all__ = ["create_user", "ensure_user", "authenticate", "login_or_register", "list_users", "get_user"]
