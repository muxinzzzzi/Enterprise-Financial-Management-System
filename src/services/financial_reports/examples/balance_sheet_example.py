"""资产负债表生成器使用示例。"""
from __future__ import annotations

from services.financial_reports.report_generators.balance_sheet import BalanceSheetGenerator


def example_usage():
    """使用示例。"""
    generator = BalanceSheetGenerator()

    # 示例输入数据
    input_data = {
        "assets": {
            "current_assets": {
                "现金": 100000.0,
                "银行存款": 500000.0,
                "应收账款": 200000.0,
                "预付账款": 50000.0,
                "存货": 300000.0,
            },
            "non_current_assets": {
                "固定资产": 1000000.0,
                "累计折旧": -200000.0,  # 负数表示扣除
                "无形资产": 200000.0,
                "长期投资": 300000.0,
            },
        },
        "liabilities": {
            "current_liabilities": {
                "应付账款": 150000.0,
                "短期借款": 300000.0,
                "应交税费": 50000.0,
                "预收账款": 100000.0,
            },
            "non_current_liabilities": {
                "长期借款": 500000.0,
                "应付债券": 200000.0,
            },
        },
        "equity": {
            "实收资本": 1000000.0,
            "资本公积": 200000.0,
            "盈余公积": 100000.0,
            "未分配利润": 50000.0,
        },
    }

    # 生成资产负债表表格
    table = generator.generate_from_dict(input_data)

    # 打印结果
    print("=" * 60)
    print("资产负债表")
    print("=" * 60)
    print()

    print("资产部分：")
    print("-" * 60)
    for row in table.asset_rows:
        indent = "  " * row.level
        prefix = ""
        if row.is_total:
            prefix = "【合计】"
        elif row.is_subtotal:
            prefix = "【小计】"
        print(f"{indent}{prefix}{row.item_name:30s} {row.amount:>15,.2f}")
    print()

    print("负债部分：")
    print("-" * 60)
    for row in table.liability_rows:
        indent = "  " * row.level
        prefix = ""
        if row.is_total:
            prefix = "【合计】"
        elif row.is_subtotal:
            prefix = "【小计】"
        print(f"{indent}{prefix}{row.item_name:30s} {row.amount:>15,.2f}")
    print()

    print("股东权益部分：")
    print("-" * 60)
    for row in table.equity_rows:
        indent = "  " * row.level
        prefix = ""
        if row.is_total:
            prefix = "【合计】"
        elif row.is_subtotal:
            prefix = "【小计】"
        print(f"{indent}{prefix}{row.item_name:30s} {row.amount:>15,.2f}")
    print()

    print("=" * 60)
    print("汇总信息：")
    print(f"流动资产小计:     {table.current_assets_subtotal:>15,.2f}")
    print(f"非流动资产小计:   {table.non_current_assets_subtotal:>15,.2f}")
    print(f"资产合计:         {table.total_assets:>15,.2f}")
    print()
    print(f"流动负债小计:     {table.current_liabilities_subtotal:>15,.2f}")
    print(f"非流动负债小计:   {table.non_current_liabilities_subtotal:>15,.2f}")
    print(f"负债合计:         {table.total_liabilities:>15,.2f}")
    print(f"股东权益合计:     {table.total_equity:>15,.2f}")
    print(f"负债和股东权益合计: {table.total_liabilities_and_equity:>15,.2f}")
    print()
    if table.is_balanced:
        print("✅ 报表平衡：资产 = 负债 + 股东权益")
    else:
        diff = abs(table.total_assets - table.total_liabilities_and_equity)
        print(f"⚠️ 报表不平衡：差异 {diff:,.2f}")
    print("=" * 60)


if __name__ == "__main__":
    example_usage()
