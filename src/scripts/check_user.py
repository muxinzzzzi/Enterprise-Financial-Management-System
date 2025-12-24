#!/usr/bin/env python3
"""检查和创建用户账号"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, db_session
from models.db_models import User
from services.user_service import authenticate, create_user

def check_and_create_user():
    """检查用户是否存在，如果不存在则创建"""

    email = "user1@example.com"
    password = "123456"
    name = "测试用户"

    print(f"正在检查用户 {email}...")

    # 初始化数据库
    init_db()

    # 检查用户是否存在
    with db_session() as session:
        user = session.query(User).filter_by(email=email).first()

        if user:
            print(f"用户 {email} 已存在")
            print(f"用户ID: {user.id}")
            print(f"用户名: {user.name}")
            print(f"角色: {user.role}")
            print(f"创建时间: {user.created_at}")

            # 验证密码
            auth_user = authenticate(email, password)
            if auth_user:
                print("✅ 密码验证成功")
            else:
                print("❌ 密码验证失败")
                print("正在重置密码...")
                # 重置密码
                user.password_hash = create_user(name, email, password).password_hash
                session.commit()
                print("✅ 密码已重置")
        else:
            print(f"用户 {email} 不存在，正在创建...")
            user = create_user(name=name, email=email, password=password)
            print(f"✅ 用户创建成功")
            print(f"用户ID: {user.id}")

    print("\n用户列表:")
    from services.user_service import list_users
    users = list_users()
    for u in users:
        print(f"- {u['email']} ({u['name']}) - {u['role']}")

if __name__ == "__main__":
    check_and_create_user()






