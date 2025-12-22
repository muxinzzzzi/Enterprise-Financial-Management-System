"""修复损坏的SQLite数据库文件。

如果数据库文件损坏，此脚本会尝试修复或重建数据库。
"""
from __future__ import annotations

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

from config import DATA_DIR

DB_PATH = DATA_DIR / "reconciliation.db"
DB_BACKUP_PATH = DATA_DIR / f"reconciliation_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"


def check_database() -> bool:
    """检查数据库文件是否损坏。"""
    if not DB_PATH.exists():
        print(f"数据库文件不存在: {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] == "ok":
            print("✓ 数据库文件正常")
            return True
        else:
            print(f"✗ 数据库文件损坏: {result}")
            return False
    except sqlite3.DatabaseError as e:
        print(f"✗ 数据库文件损坏: {e}")
        return False
    except Exception as e:
        print(f"✗ 检查数据库时出错: {e}")
        return False


def repair_database() -> bool:
    """尝试修复数据库。"""
    if not DB_PATH.exists():
        print("数据库文件不存在，无需修复")
        return False
    
    print("尝试修复数据库...")
    try:
        # 创建备份
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, DB_BACKUP_PATH)
            print(f"已创建备份: {DB_BACKUP_PATH}")
        
        # 尝试使用.dump和.read修复
        dump_file = DATA_DIR / "reconciliation_dump.sql"
        repaired_db = DATA_DIR / "reconciliation_repaired.db"
        
        # 导出数据
        try:
            conn_old = sqlite3.connect(str(DB_PATH))
            with open(dump_file, 'w', encoding='utf-8') as f:
                for line in conn_old.iterdump():
                    f.write(f"{line}\n")
            conn_old.close()
            print(f"已导出数据到: {dump_file}")
        except Exception as e:
            print(f"导出数据失败: {e}")
            return False
        
        # 导入到新数据库
        try:
            conn_new = sqlite3.connect(str(repaired_db))
            with open(dump_file, 'r', encoding='utf-8') as f:
                conn_new.executescript(f.read())
            conn_new.close()
            print(f"已创建修复后的数据库: {repaired_db}")
        except Exception as e:
            print(f"导入数据失败: {e}")
            dump_file.unlink(missing_ok=True)
            return False
        
        # 验证修复后的数据库
        try:
            conn_check = sqlite3.connect(str(repaired_db))
            cursor = conn_check.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            conn_check.close()
            
            if result and result[0] == "ok":
                # 替换原数据库
                DB_PATH.unlink()
                repaired_db.rename(DB_PATH)
                dump_file.unlink(missing_ok=True)
                print("✓ 数据库修复成功")
                return True
            else:
                print(f"✗ 修复后的数据库仍然损坏: {result}")
                repaired_db.unlink(missing_ok=True)
                dump_file.unlink(missing_ok=True)
                return False
        except Exception as e:
            print(f"验证修复后的数据库失败: {e}")
            repaired_db.unlink(missing_ok=True)
            dump_file.unlink(missing_ok=True)
            return False
            
    except Exception as e:
        print(f"修复过程出错: {e}")
        return False


def recreate_database() -> bool:
    """删除损坏的数据库文件，让系统重新创建。"""
    if not DB_PATH.exists():
        print("数据库文件不存在，无需删除")
        return True
    
    try:
        # 创建备份
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, DB_BACKUP_PATH)
            print(f"已创建备份: {DB_BACKUP_PATH}")
        
        # 删除损坏的数据库
        DB_PATH.unlink()
        print(f"已删除损坏的数据库文件: {DB_PATH}")
        print("系统将在下次启动时自动创建新的数据库")
        return True
    except Exception as e:
        print(f"删除数据库文件失败: {e}")
        return False


def main():
    """主函数。"""
    print("=" * 60)
    print("SQLite 数据库修复工具")
    print("=" * 60)
    print(f"数据库文件: {DB_PATH}")
    print()
    
    # 检查数据库
    if check_database():
        print("\n数据库正常，无需修复。")
        return
    
    print("\n数据库已损坏，开始修复流程...")
    print()
    
    # 尝试修复
    if repair_database():
        print("\n✓ 数据库修复成功！")
        return
    
    print("\n修复失败，准备重建数据库...")
    print("警告: 这将删除所有现有数据！")
    
    response = input("\n是否继续？(y/N): ").strip().lower()
    if response != 'y':
        print("已取消操作。")
        return
    
    # 重建数据库
    if recreate_database():
        print("\n✓ 已删除损坏的数据库文件")
        print("请重新启动应用程序，系统将自动创建新的数据库。")
    else:
        print("\n✗ 删除数据库文件失败")


if __name__ == "__main__":
    main()



















