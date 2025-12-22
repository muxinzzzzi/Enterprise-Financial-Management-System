# 数据库修复指南

## 错误说明

如果你遇到以下错误：
```
sqlite3.DatabaseError: database disk image is malformed
```

这表示SQLite数据库文件已损坏。常见原因：
- 程序在写入数据库时被强制终止
- 系统断电或崩溃
- 磁盘空间不足
- 磁盘错误

## 解决方案

### 方案一：使用修复脚本（推荐）

1. **运行修复脚本**：
   ```bash
   cd src
   python fix_database.py
   ```

2. **脚本会自动**：
   - 检查数据库是否损坏
   - 尝试修复数据库（导出并重新导入数据）
   - 如果修复失败，会询问是否重建数据库

3. **如果修复成功**：
   - 数据库已恢复，可以正常使用
   - 备份文件保存在 `src/data/reconciliation_backup_*.db`

4. **如果修复失败**：
   - 脚本会询问是否删除损坏的数据库
   - 选择"y"后，系统会在下次启动时自动创建新数据库
   - **注意：这会丢失所有数据！**

### 方案二：手动修复

1. **备份数据库文件**：
   ```bash
   cd src/data
   copy reconciliation.db reconciliation_backup.db
   ```

2. **尝试使用SQLite命令行工具修复**：
   ```bash
   sqlite3 reconciliation.db ".dump" > dump.sql
   sqlite3 reconciliation_repaired.db < dump.sql
   ```

3. **验证修复后的数据库**：
   ```bash
   sqlite3 reconciliation_repaired.db "PRAGMA integrity_check;"
   ```

4. **如果验证通过，替换原文件**：
   ```bash
   del reconciliation.db
   ren reconciliation_repaired.db reconciliation.db
   ```

### 方案三：重建数据库（会丢失数据）

如果修复失败，可以删除损坏的数据库文件，让系统重新创建：

1. **删除数据库文件**：
   ```bash
   cd src/data
   del reconciliation.db
   ```

2. **重新启动应用程序**：
   ```bash
   python app.py
   ```

   系统会自动创建新的空数据库。

## 预防措施

1. **定期备份数据库**：
   ```bash
   # Windows
   copy src\data\reconciliation.db src\data\backup\reconciliation_%date%.db
   
   # Linux/Mac
   cp src/data/reconciliation.db src/data/backup/reconciliation_$(date +%Y%m%d).db
   ```

2. **确保磁盘空间充足**

3. **正常关闭应用程序**（不要强制终止）

4. **避免在数据库写入时断电或强制关闭**

## 数据恢复

如果数据库损坏且没有备份：

- **已上传的票据文件**：通常保存在 `src/data/input/` 目录，可以重新上传
- **用户数据**：需要重新注册用户
- **处理结果**：需要重新处理票据

## 技术支持

如果修复脚本无法解决问题，请：
1. 检查磁盘空间和权限
2. 检查是否有其他程序正在使用数据库文件
3. 查看完整的错误日志



















