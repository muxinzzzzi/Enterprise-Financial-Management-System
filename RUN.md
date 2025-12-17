# 本地运行快速指引（可直接复制粘贴）

## 环境要求
- Python 3.10+（macOS/Ubuntu 已预装可用 `python3`）
- Git
- 可选：`curl`/`wget` 用于快速获取依赖

## 全量快速启动（首次克隆）
```bash
# 1) 克隆仓库（如已克隆可跳过）
git clone git@github.com:muxinzzzzi/Enterprise-Financial-Management-System.git
cd Enterprise-Financial-Management-System

# 2) 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate   # Windows 可用: .venv\Scripts\activate

# 3) 安装依赖
pip install --upgrade pip
pip install -r src/requirements.txt

# 4) 准备环境变量（如仓库已带 .env 可直接使用；若需覆盖可执行）
cat > .env <<'EOF'
# LLM / DeepSeek 配置
DEEPSEEK_API_KEY=sk-a2ca8484cbf042b29d609242f12453f8
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 百度票据OCR配置
# 应用名称: 票据识别（HTTP SDK 不需要）
BAIDU_APP_NAME=票据识别
BAIDU_APP_ID=121280012
BAIDU_API_KEY=530ZIMFJF15RQXzMZiq10jPa
BAIDU_SECRET_KEY=Zr0usGzHF3UWJtyauKyq62XyudDK6Ggo

# 其他可选设置
OCR_ENDPOINTS=
DEFAULT_CURRENCY=CNY
ENABLE_POLICY_RAG=true
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
DUPLICATE_THRESHOLD=0.92
ANOMALY_SIGMA=2.5
EOF

# 5) 运行服务（默认端口 9000，如需调整可设置 PORT=xxxx）
python src/app.py
# 然后访问 http://localhost:9000 （浏览器会自动跳转到登录页/看板）
```

## 已有仓库、已装依赖情况下的新终端快速启动
```bash
cd /Users/muxin/Desktop/对账系统   # 或你的仓库路径
source .venv/bin/activate
python src/app.py
```

## 备注
- 数据与输出目录位于 `src/data`（已随仓库提交），首次启动无需手动建库，程序会自动初始化 SQLite。
- 如需更换端口：`PORT=8080 python src/app.py`
- 如遇依赖问题，可重新安装：`pip install -r src/requirements.txt --force-reinstall`

