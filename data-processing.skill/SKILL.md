---
name: data-processing
description: "K1/K2 套利数据标准化处理流水线。处理订单数据/token数据/日报数据，支持命令行和 Python 调用。当需要清洗数据、标准化导出文件、处理原始 Excel/CSV 时触发。使用方式：python db/scripts/data_processor.py --contract k1 --type order --date 2026-03-24 --input /path/to/file"
---

# Data Processing Pipeline

> **数据路径约定：** 原始文件上传到 `db/files/{数据类型}/`，处理后也在同一位置。
> **输出格式：** 统一 CSV，不再输出 Excel。
> 用户确认无误后，删除原始导出文件。

## 功能概述

标准化处理 K1/K2 套利策略的原始导出数据，生成清洗后的 CSV 规范文件。

## 支持数据类型

| 类型 | data_type 参数 | 输入格式 | 输出格式 | 处理要点 |
|------|----------------|---------|---------|---------|
| 订单数据 | `order` | Excel (.xlsx) | **CSV (.csv)** | 列名中文化 + wei换算 + 过滤成功订单 |
| token数据 | `token` | CSV/Excel | **CSV (.csv)** | HTML清理 + 精度格式化 |
| 日报数据 | `daily` | CSV/Excel | **CSV (.csv)** | 补日期列 + 精度整理 |

## 脚本位置

```
db/scripts/data_processor.py
db/scripts/data_loader.py
```

## 使用方式

### Python 调用（推荐）

```python
import sys
sys.path.insert(0, '/Users/yy/.openclaw/workspace/db/scripts')
from data_processor import process_data

# 订单数据
df = process_data('k1', 'order', '2026-03-24', '/path/to/k1_export_orders_20260324.xlsx')

# token 数据
df = process_data('k1', 'token', '2026-03-27', '/path/to/export_2026-03-27.csv')

# 日报数据
df = process_data('k1', 'daily', '2026-03-26', '/path/to/export_2026-03-26.csv')
```

### 命令行

```bash
python3 db/scripts/data_processor.py \
    --contract k1 --type order --date 2026-03-24 \
    --input /path/to/k1_export_orders_20260324.xlsx
```

## 处理详情

### 订单数据 (order)

**处理步骤：**
1. 读取 Excel（66列，英文）
2. 列名标准化：英文 → 中文（54列）
3. 删除多余列（12列）
4. 数据类型校正（时间/区块号/状态）
5. wei 单位换算：
   - BNB 持仓：÷ 1e18
   - token/stable 持仓：÷ 10^decimals
6. 过滤成功订单（状态=1）
7. 验算：捆绑费误差 < 0.01
8. 保存 CSV

**输出文件：**
```
k1_订单数据_2026-03-24.csv
k2_订单数据_2026-03-24.csv
```

### token数据 (token)

**处理步骤：**
1. 读取 CSV/Excel（31列，中文）
2. 清理 HTML 标签（`清空数据` 列）
3. 数值精度格式化（2位小数）
4. 字符串去空格 / 清理多行值

**输出文件：**
```
k1_token数据_2026-03-27.csv
k2_token数据_2026-03-27.csv
```

### 日报数据 (daily)

**处理步骤：**
1. 读取 CSV/Excel（8列，中文，无日期列）
2. 从文件名提取日期（`YYYY-MM-DD`）插入首列
3. 数值精度整理（4位小数）

**输出文件：**
```
k1_日报数据_2026-03-26.csv
k2_日报数据_2026-03-26.csv
```

## 输出位置

默认输出至 `db/files/{数据类型}/`

```
db/files/
├── 订单数据/
│   ├── k1_订单数据_2026-03-24.csv
│   └── k2_订单数据_2026-03-24.csv
├── token数据/
│   ├── k1_token数据_2026-03-27.csv
│   └── k2_token数据_2026-03-27.csv
└── 日报数据/
    ├── k1_日报数据_2026-03-26.csv
    └── k2_日报数据_2026-03-26.csv
```

## 数据加载

```python
from data_loader import load_order_data, load_token_data, load_daily_data

df_order = load_order_data('k1', '2026-03-24')  # 返回 DataFrame
df_token = load_token_data('k1', '2026-03-27')
df_daily = load_daily_data('k1', '2026-03-26')
```

## 后续分析

清洗完成后，接入分析流程：

```python
from data_loader import load_order_data
from core_formulas import calc_gap, calc_slippage, calc_alpha

df = load_order_data('k1', '2026-03-24')
df = calc_slippage(df)
df = calc_alpha(df)
```

详见：`db/scripts/ANALYSIS_REGISTRY.md`
