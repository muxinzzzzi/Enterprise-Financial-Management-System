# 资产负债表模块使用说明

## 功能概述

资产负债表模块 (`balance_sheet.py`) 提供了从Python字典生成资产负债表表格数据的功能。

## 输入格式

输入是一个Python字典，包含以下结构：

```python
{
    "assets": {
        "current_assets": {
            "现金": 100000.0,
            "银行存款": 500000.0,
            "应收账款": 200000.0,
            "预付账款": 50000.0,
            "存货": 300000.0,
            # ... 更多流动资产项目
        },
        "non_current_assets": {
            "固定资产": 1000000.0,
            "累计折旧": -200000.0,  # 负数表示扣除
            "无形资产": 200000.0,
            "长期投资": 300000.0,
            # ... 更多非流动资产项目
        }
    },
    "liabilities": {
        "current_liabilities": {
            "应付账款": 150000.0,
            "短期借款": 300000.0,
            "应交税费": 50000.0,
            "预收账款": 100000.0,
            # ... 更多流动负债项目
        },
        "non_current_liabilities": {
            "长期借款": 500000.0,
            "应付债券": 200000.0,
            # ... 更多非流动负债项目
        }
    },
    "equity": {
        "实收资本": 1000000.0,
        "资本公积": 200000.0,
        "盈余公积": 100000.0,
        "未分配利润": 50000.0,
        # ... 更多股东权益项目
    }
}
```

## 输出格式

输出是一个 `BalanceSheetTable` 对象，包含以下字段：

- `rows`: 所有行的列表（资产+负债+股东权益）
- `asset_rows`: 资产部分的行列表
- `liability_rows`: 负债部分的行列表
- `equity_rows`: 股东权益部分的行列表
- `current_assets_subtotal`: 流动资产小计
- `non_current_assets_subtotal`: 非流动资产小计
- `total_assets`: 资产合计
- `current_liabilities_subtotal`: 流动负债小计
- `non_current_liabilities_subtotal`: 非流动负债小计
- `total_liabilities`: 负债合计
- `total_equity`: 股东权益合计
- `total_liabilities_and_equity`: 负债和股东权益合计
- `is_balanced`: 是否平衡（资产 = 负债 + 股东权益）

每行 (`BalanceSheetRow`) 包含：
- `item_name`: 项目名称
- `amount`: 金额
- `level`: 层级（0=主分类，1=子项目）
- `is_subtotal`: 是否为小计行
- `is_total`: 是否为合计行

## 使用示例

```python
from services.financial_reports.report_generators.balance_sheet import BalanceSheetGenerator

# 创建生成器
generator = BalanceSheetGenerator()

# 准备输入数据
input_data = {
    "assets": {
        "current_assets": {
            "现金": 100000.0,
            "银行存款": 500000.0,
        },
        "non_current_assets": {
            "固定资产": 1000000.0,
        }
    },
    "liabilities": {
        "current_liabilities": {
            "应付账款": 150000.0,
        },
        "non_current_liabilities": {
            "长期借款": 500000.0,
        }
    },
    "equity": {
        "实收资本": 1000000.0,
        "未分配利润": -50000.0,
    }
}

# 生成表格
table = generator.generate_from_dict(input_data)

# 访问结果
print(f"资产合计: {table.total_assets}")
print(f"负债合计: {table.total_liabilities}")
print(f"股东权益合计: {table.total_equity}")
print(f"是否平衡: {table.is_balanced}")

# 遍历所有行
for row in table.rows:
    indent = "  " * row.level
    print(f"{indent}{row.item_name}: {row.amount}")
```

## 表格结构

生成的表格结构如下：

```
资产
  流动资产
    现金
    银行存款
    ...
  流动资产小计
  非流动资产
    固定资产
    ...
  非流动资产小计
资产合计

负债
  流动负债
    应付账款
    ...
  流动负债小计
  非流动负债
    长期借款
    ...
  非流动负债小计
负债合计

股东权益
  实收资本
  资本公积
  ...
股东权益合计

负债和股东权益合计
```

## 注意事项

1. 所有金额应为浮点数
2. 负数金额表示扣除项（如累计折旧）
3. 系统会自动计算各分类小计和合计
4. 系统会自动验证平衡关系：资产 = 负债 + 股东权益
5. 如果数据不平衡，`is_balanced` 字段为 `False`
