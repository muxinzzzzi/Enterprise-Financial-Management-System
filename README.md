# 企业财务对账管理系统

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个基于 AI 的智能财务对账管理系统，支持发票识别、自动对账、财务报表生成等功能。

[功能特性](#功能特性) • [快速开始](#快速开始) • [配置说明](#配置说明) • [使用指南](#使用指南) • [项目结构](#项目结构)

</div>

---

## 📋 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [检测百度 OCR 配置](#检测百度-ocr-配置)
- [运行项目](#运行项目)
- [使用指南](#使用指南)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [开发说明](#开发说明)

---

## ✨ 功能特性

### 🎯 核心功能
- **智能票据识别**：支持发票、出租车票、增值税发票等多种票据的 OCR 识别
- **自动对账处理**：基于 AI 的智能对账引擎，自动匹配和验证财务数据
- **异常检测**：智能识别重复票据、异常金额、税率异常等问题
- **政策合规验证**：基于 RAG 技术的财务政策自动审核
- **财务报表生成**：自动生成资产负债表、利润表、现金流量表
- **会计分录**：AI 自动生成标准会计分录和记账凭证

### 🚀 特色功能
- **批量票据处理**：支持批量上传和处理票据图片/PDF
- **智能分类**：自动分类费用类型（差旅、办公、餐饮等）
- **数据标准化**：自动规范化供应商名称、日期、金额格式
- **审核工作流**：支持票据审核、修改、驳回等完整流程
- **数据分析看板**：实时财务数据可视化和趋势分析
- **AI 智能问答**：基于财务数据的自然语言查询

---

## 🛠 技术栈

### 后端框架
- **Flask 3.0**：Web 应用框架
- **SQLAlchemy 2.0**：ORM 数据库操作
- **Pydantic 2.8**：数据验证和序列化

### AI & 机器学习
- **DeepSeek API**：大语言模型（LLM）
- **Sentence Transformers**：语义向量化和相似度计算
- **百度 OCR API**：票据识别

### 数据处理
- **PDFPlumber**：PDF 文档解析
- **OpenPyXL**：Excel 文件处理
- **ReportLab & WeasyPrint**：PDF 报表生成

### 数据库
- **SQLite**：轻量级关系型数据库（可升级为 PostgreSQL/MySQL）

---

## 📦 环境要求

### 系统要求
- **操作系统**：macOS / Linux / Windows
- **Python**：3.10 或更高版本
- **Git**：用于克隆仓库
- **内存**：建议 4GB 以上
- **磁盘空间**：至少 2GB 可用空间

### API 密钥（必需）
- **DeepSeek API Key**：[申请地址](https://platform.deepseek.com/)
- **百度 OCR API**：[申请地址](https://ai.baidu.com/tech/ocr)

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/muxinzzzzi/Enterprise-Financial-Management-System.git
cd Enterprise-Financial-Management-System
```

### 2. 创建虚拟环境

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install --upgrade pip
pip install -r src/requirements.txt
```

> **提示**：首次安装可能需要 5-10 分钟，请耐心等待。

### 4. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# 方式一：手动创建
nano .env

# 方式二：从模板复制
cp .env.example .env  # 如果有模板文件
```

填入以下配置：

```env
# LLM 配置（必需）
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 百度 OCR 配置（必需）
BAIDU_APP_ID=your_baidu_app_id
BAIDU_API_KEY=your_baidu_api_key
BAIDU_SECRET_KEY=your_baidu_secret_key

# 可选配置
DEFAULT_CURRENCY=CNY
ENABLE_POLICY_RAG=true
DUPLICATE_THRESHOLD=0.92
ANOMALY_SIGMA=2.5
```

> **重要**：请替换 `your_*_here` 为实际的 API 密钥。

### 5. 启动服务

```bash
python src/app.py
```

成功启动后，你会看到：

```
 * Running on http://127.0.0.1:9000
```

### 6. 访问系统

在浏览器中打开：**http://localhost:9000**

默认登录账号：
- **用户名**：`admin`
- **密码**：`admin123`

---

## ⚙️ 配置说明

### 环境变量详解

| 变量名 | 说明 | 默认值 | 是否必需 |
|--------|------|--------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | - | ✅ 必需 |
| `DEEPSEEK_BASE_URL` | API 基础 URL | `https://api.deepseek.com` | 可选 |
| `DEEPSEEK_MODEL` | 使用的模型 | `deepseek-chat` | 可选 |
| `BAIDU_APP_ID` | 百度 OCR 应用 ID | - | ✅ 必需 |
| `BAIDU_API_KEY` | 百度 OCR API Key | - | ✅ 必需 |
| `BAIDU_SECRET_KEY` | 百度 OCR Secret Key | - | ✅ 必需 |
| `DEFAULT_CURRENCY` | 默认货币 | `CNY` | 可选 |
| `ENABLE_POLICY_RAG` | 启用政策 RAG | `true` | 可选 |
| `DUPLICATE_THRESHOLD` | 重复检测阈值 | `0.92` | 可选 |
| `ANOMALY_SIGMA` | 异常检测标准差 | `2.5` | 可选 |
| `PORT` | 服务端口 | `9000` | 可选 |

### 数据库配置

系统默认使用 SQLite，数据库文件位于 `src/data/reconciliation.db`。

如需使用 PostgreSQL 或 MySQL，修改 `.env`：

```env
# PostgreSQL 示例
DATABASE_URL=postgresql://user:password@localhost/dbname

# MySQL 示例
DATABASE_URL=mysql+pymysql://user:password@localhost/dbname
```

---

## 🔍 检测百度 OCR 配置

使用内置脚本验证 `.env` 中的百度 OCR 配置是否生效，并跑通 ingestion + OCR 流程：

```bash
# 1) 激活虚拟环境
source .venv/bin/activate

# 2) 运行检测脚本（可替换为自己的图片路径）
python src/scripts/test_ocr.py \
  --image InvoiceDatasets-master/dataset/images/taxi_test/00010122_0011978006.png
```

运行后终端会打印：
- 配置检查（是否已配置 BAIDU_APP_ID/BAIDU_API_KEY/BAIDU_SECRET_KEY）
- 使用的 OCR 引擎、置信度、文本前 400 字符
- 若配置缺失或调用失败，会在日志中提示原因

Windows 用户可将第一行改为 `.venv\Scripts\activate`。

---

## 🎮 运行项目

### 开发模式

```bash
python src/app.py
```

### 生产模式（使用 Gunicorn）

```bash
gunicorn -w 4 -b 0.0.0.0:9000 src.app:app
```

### 指定端口运行

```bash
PORT=8080 python src/app.py
```

### 后台运行

```bash
# macOS / Linux
nohup python src/app.py > app.log 2>&1 &

# 停止服务
ps aux | grep app.py
kill <PID>
```

---

## 📖 使用指南

### 1. 上传票据

1. 登录系统后进入主界面
2. 点击「上传票据」按钮
3. 选择图片（JPG/PNG）或 PDF 文件
4. 系统自动进行 OCR 识别和字段提取

### 2. 批量导入

```bash
# 将票据图片放入 src/data/input/ 目录
cp /path/to/invoices/* src/data/input/

# 运行批量导入脚本
python src/scripts/bulk_upload_tickets.py
```

### 3. 对账处理

1. 在票据列表中选择待对账的票据
2. 点击「开始对账」
3. 系统自动进行：
   - 字段验证
   - 重复检测
   - 异常识别
   - 政策合规审核
4. 查看对账结果和建议

### 4. 生成财务报表

1. 进入「财务报表」模块
2. 选择报表类型：
   - 资产负债表
   - 利润表
   - 现金流量表
3. 选择日期范围
4. 点击「生成报表」
5. 支持导出为 PDF 或 Markdown

### 5. 会计分录

1. 选择已对账的票据
2. 点击「生成分录」
3. AI 自动生成标准会计分录
4. 支持手动调整和审核
5. 导出为记账凭证 PDF

### 6. 数据分析

1. 进入「数据看板」
2. 查看实时统计：
   - 费用趋势分析
   - 供应商分布
   - 异常票据统计
   - 类别占比
3. 支持时间范围筛选

---

## 📁 项目结构

```
Enterprise-Financial-Management-System/
├── src/                          # 源代码目录
│   ├── app.py                    # Flask 应用主入口
│   ├── config.py                 # 配置管理
│   ├── database.py               # 数据库初始化
│   ├── llm_client.py             # LLM 客户端封装
│   ├── models/                   # 数据模型
│   │   ├── db_models.py          # SQLAlchemy 数据库模型
│   │   ├── schemas.py            # Pydantic 数据模式
│   │   └── financial_schemas.py  # 财务相关模式
│   ├── services/                 # 业务服务层
│   │   ├── ingestion/            # 票据录入服务
│   │   │   ├── ocr_service.py    # OCR 识别
│   │   │   └── ingestion_service.py
│   │   ├── extraction/           # 信息提取服务
│   │   │   ├── extraction_service.py
│   │   │   ├── categorization_service.py
│   │   │   └── normalization_service.py
│   │   ├── accounting/           # 会计处理服务
│   │   │   ├── journal_service.py      # 分录生成
│   │   │   ├── ai_accountant.py        # AI 会计师
│   │   │   └── persistence_service.py  # 数据持久化
│   │   ├── analytics/            # 分析服务
│   │   │   ├── analytics_service.py
│   │   │   ├── anomaly_service.py      # 异常检测
│   │   │   ├── dashboard_service.py    # 看板
│   │   │   └── report_service.py       # 报表
│   │   ├── policy_rag/           # 政策 RAG 服务
│   │   │   ├── policy_service.py
│   │   │   ├── rag_retriever.py
│   │   │   └── knowledge_base_service.py
│   │   ├── assistants/           # 智能助手
│   │   │   ├── assistant_service.py
│   │   │   └── review_service.py
│   │   └── financial_reports/    # 财务报表
│   │       ├── report_service.py
│   │       ├── data_aggregator.py
│   │       └── report_generators/
│   ├── pipelines/                # 处理流程管道
│   │   └── reconciliation_pipeline.py
│   ├── repositories/             # 数据访问层
│   │   ├── audit_log.py          # 审计日志
│   │   └── vector_store.py       # 向量存储
│   ├── scripts/                  # 工具脚本
│   │   ├── bulk_upload_tickets.py
│   │   └── bulk_ingest_archive.py
│   ├── templates/                # HTML 模板
│   │   ├── dashboard.html
│   │   └── login.html
│   ├── static/                   # 静态资源
│   │   ├── css/
│   │   └── js/
│   ├── data/                     # 数据目录
│   │   ├── input/                # 输入票据
│   │   ├── output/               # 输出结果
│   │   ├── reports/              # 生成的报表
│   │   ├── cache/                # 缓存文件
│   │   └── reconciliation.db     # SQLite 数据库
│   └── requirements.txt          # Python 依赖
├── .env                          # 环境变量配置
├── .gitignore                    # Git 忽略规则
├── README.md                     # 项目说明文档
└── RUN.md                        # 快速运行指南
```

---

## ❓ 常见问题

### Q1: 启动时报错 "No module named 'xxx'"？

**解决方案**：
```bash
# 确保虚拟环境已激活
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate      # Windows

# 重新安装依赖
pip install -r src/requirements.txt --force-reinstall
```

### Q2: OCR 识别失败或不准确？

**可能原因**：
1. 百度 OCR API 密钥配置错误
2. 图片质量太低或格式不支持
3. API 调用配额已用完

**解决方案**：
- 检查 `.env` 中的百度 API 配置
- 使用清晰的票据扫描图片（建议 300 DPI 以上）
- 确认百度 API 账户余额充足

### Q3: 端口 9000 被占用？

**解决方案**：
```bash
# 方式一：更换端口
PORT=8080 python src/app.py

# 方式二：查找并关闭占用端口的进程
lsof -i :9000
kill -9 <PID>
```

### Q4: 数据库文件损坏或需要重置？

**解决方案**：
```bash
# 备份现有数据库
cp src/data/reconciliation.db src/data/reconciliation.db.backup

# 删除并重新初始化
rm src/data/reconciliation.db
python src/app.py  # 启动时会自动创建新数据库
```

### Q5: 如何导入历史数据？

**解决方案**：
```bash
# 将票据图片放入 input 目录
cp /path/to/historical/invoices/* src/data/input/

# 批量导入
python src/scripts/bulk_upload_tickets.py
```

### Q6: 内存占用过高？

**解决方案**：
- 减少 `ANALYTICS_CACHE_LIMIT` 配置值
- 定期清理 `src/data/cache/` 目录
- 如果使用批量处理，减少单批次数量

### Q7: DeepSeek API 调用失败？

**排查步骤**：
1. 检查 API Key 是否正确
2. 确认网络连接正常
3. 检查 API 配额是否用完
4. 查看 `src/data/cache/audit.log` 日志

---

## 🔧 开发说明

### 添加新的票据类型

1. 在 `src/services/ingestion/ocr_service.py` 添加识别逻辑
2. 在 `src/services/extraction/extraction_service.py` 添加字段提取规则
3. 更新 `src/models/schemas.py` 中的数据模型

### 自定义财务政策

1. 将政策文档（PDF/TXT/DOCX）放入 `src/data/policy/` 目录
2. 系统会自动加载并构建 RAG 向量库
3. 在对账时自动进行政策合规检查

### 扩展 API

参考 `src/app.py` 中的路由定义：

```python
@app.route('/api/custom-endpoint', methods=['POST'])
def custom_endpoint():
    # 你的业务逻辑
    return jsonify({"status": "success"})
```

### 单元测试

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行测试
pytest tests/

# 生成覆盖率报告
pytest --cov=src tests/
```

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📮 联系方式

如有问题或建议，请通过以下方式联系：

- **GitHub Issues**: [提交问题](https://github.com/muxinzzzzi/Enterprise-Financial-Management-System/issues)
- **Email**: muxinzi3379@outlook.com

---

## 🙏 致谢

感谢以下开源项目：
- [Flask](https://flask.palletsprojects.com/)
- [DeepSeek](https://platform.deepseek.com/)
- [百度 AI](https://ai.baidu.com/)
- [Sentence Transformers](https://www.sbert.net/)

---

<div align="center">
Made with ❤️ by the Development Team
</div>

