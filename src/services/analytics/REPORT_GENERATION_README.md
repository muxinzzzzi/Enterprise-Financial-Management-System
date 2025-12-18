# 报表生成模块使用说明

本模块实现了三类报表的生成功能，并集成了AI关键点服务。

## 功能概述

### 三类报表

1. **单张票据审核报告 (Invoice Audit Report)**
   - 包含票据基本信息
   - 审核结论（通过/需补充/不合规）
   - 证据链
   - 风险点分析
   - 修改建议

2. **周期汇总报表 (Period Summary Report)**
   - 本期花费结构（按类别、供应商统计）
   - 合规率统计
   - 异常类型分布
   - Top供应商和Top类别

3. **审计追溯与整改清单 (Audit Trail & Action List)**
   - 需要补材料的票据
   - 超标准的票据
   - 疑似重复/异常的票据
   - 按优先级排序

### AI关键点

1. **AI关键点A：审核结论自动生成**
   - 基于结构化字段、规则校验结果与异常检测结果
   - 自动生成结论状态、关键问题摘要、风险等级

2. **AI关键点B：问题归因与类型化**
   - 将票据问题归类到统一的问题体系
   - 输出问题类型、严重程度、置信度

## API端点

### 1. 生成单张票据审核报告

**POST** `/api/v1/reports/invoice_audit`

请求体：
```json
{
  "document_id": "doc_xxx",
  "save_file": true
}
```

响应：
```json
{
  "success": true,
  "report": "# 单张票据审核报告\n\n...",
  "document_id": "doc_xxx"
}
```

### 2. 生成周期汇总报表

**POST** `/api/v1/reports/period_summary`

请求体：
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "user_id": "usr_xxx",
  "period_type": "月",
  "period_label": "2025年10期",
  "save_file": true
}
```

响应：
```json
{
  "success": true,
  "report": "# 周期汇总报表\n\n...",
  "document_count": 100,
  "period_type": "月",
  "period_label": "2025年10期"
}
```

### 3. 生成审计追溯与整改清单

**POST** `/api/v1/reports/audit_trail`

请求体：
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "user_id": "usr_xxx",
  "save_file": true
}
```

响应：
```json
{
  "success": true,
  "report": "# 审计追溯与整改清单\n\n...",
  "document_count": 100
}
```

### 4. 生成所有报表

**POST** `/api/v1/reports/all`

请求体：
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "user_id": "usr_xxx",
  "period_type": "月",
  "period_label": "2025年10期",
  "save_files": true
}
```

响应：
```json
{
  "success": true,
  "reports": {
    "period_summary": "# 周期汇总报表\n\n...",
    "audit_trail": "# 审计追溯与整改清单\n\n...",
    "invoice_reports": {
      "doc_xxx": "# 单张票据审核报告\n\n...",
      ...
    }
  },
  "document_count": 100,
  "period_type": "月",
  "period_label": "2025年10期"
}
```

## 报表存储

报表默认保存在 `data/reports/` 目录下，文件名为：
- 单张票据审核报告：`invoice_audit_{document_id}_{timestamp}.md`
- 周期汇总报表：`period_summary_{period_type}_{timestamp}.md`
- 审计追溯与整改清单：`audit_trail_{timestamp}.md`

## 使用示例

### Python代码示例

```python
from services.analytics.advanced_report_service import AdvancedReportService
from llm_client import LLMClient
from pathlib import Path

# 初始化服务
llm_client = LLMClient()
report_service = AdvancedReportService(
    llm_client, 
    output_dir=Path("data/reports")
)

# 生成单张票据审核报告
report = report_service.generate_invoice_audit_report(
    document_result,
    policy_flags,
    anomalies,
    duplicate_candidates
)
```

### cURL示例

```bash
# 生成单张票据审核报告
curl -X POST http://localhost:9000/api/v1/reports/invoice_audit \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_xxx",
    "save_file": true
  }'

# 生成周期汇总报表
curl -X POST http://localhost:9000/api/v1/reports/period_summary \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "period_type": "月",
    "period_label": "2025年10期"
  }'
```

## 问题类型体系

预定义的问题类型包括：
- 抬头不合规
- 金额超标准
- 缺少必要材料
- 类别疑似错误
- 疑似重复报销
- 日期异常
- 税额异常
- OCR识别错误
- 政策规则冲突
- 其他异常

## 注意事项

1. 单张票据审核报告：如果票据数量超过50张，批量生成所有报告时不会为每张票据生成单独报告（避免生成过多文件）
2. 报表生成需要LLM服务支持，确保已配置DEEPSEEK_API_KEY
3. 报表以Markdown格式存储，便于阅读和后续处理
