"""为invoices表添加索引以提升查询性能。"""
from __future__ import annotations

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from sqlalchemy import text

from database import db_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_indexes():
    """添加索引到documents表（发票数据）。"""
    # 注意：实际的发票数据存储在documents表中，不是invoices表
    indexes = [
        ("idx_documents_created_at", "CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at)"),
        ("idx_documents_vendor", "CREATE INDEX IF NOT EXISTS idx_documents_vendor ON documents(vendor)"),
        ("idx_documents_category", "CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category)"),
        ("idx_documents_status", "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)"),
        ("idx_documents_amount", "CREATE INDEX IF NOT EXISTS idx_documents_amount ON documents(amount)"),
        ("idx_documents_user_id", "CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)"),
    ]
    
    with db_session() as db:
        for index_name, sql in indexes:
            try:
                logger.info(f"创建索引: {index_name}")
                db.execute(text(sql))
                db.commit()
                logger.info(f"✓ 索引 {index_name} 创建成功")
            except Exception as e:
                logger.error(f"✗ 创建索引 {index_name} 失败: {e}")
                db.rollback()
    
    logger.info("索引创建完成")


if __name__ == "__main__":
    add_indexes()

