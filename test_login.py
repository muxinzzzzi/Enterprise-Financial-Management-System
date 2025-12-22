#!/usr/bin/env python3
"""
简单的登录测试脚本
用于验证用户账号是否可以正常登录
"""

import sys
import os
sys.path.append('src')

from database import init_db
from services.user_service import authenticate, list_users

def test_login():
    """测试登录功能"""

    print("🔍 检查用户账号...")
    init_db()

    # 列出所有用户
    users = list_users()
    print(f"📋 系统中存在的用户 ({len(users)} 个):")
    for user in users:
        print(f"  - {user['email']} ({user['name']}) - 角色: {user['role']}")

    print("\n🔐 测试登录...")

    # 测试指定账号
    email = "user1@example.com"
    password = "123456"

    user = authenticate(email, password)
    if user:
        print("✅ 登录成功！")
        print(f"   用户名: {user.name}")
        print(f"   邮箱: {user.email}")
        print(f"   角色: {user.role}")
        print(f"   用户ID: {user.id}")
        return True
    else:
        print("❌ 登录失败")
        print("   可能的原因:")
        print("   - 用户不存在")
        print("   - 密码错误")
        return False

if __name__ == "__main__":
    success = test_login()
    if success:
        print("\n🎉 账号恢复成功！您可以使用以下信息登录:")
        print("   邮箱: user1@example.com")
        print("   密码: 123456")
        print("\n💡 如果应用无法启动，请尝试:")
        print("   1. 安装依赖: pip install -r src/requirements.txt")
        print("   2. 启动应用: python src/app.py")
        print("   3. 访问: http://localhost:9000")
    else:
        print("\n❌ 账号恢复失败，请联系管理员")
