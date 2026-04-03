"""
数据处理流水线脚本
版本: v2.0 | 更新: 2026-03-27

功能: 标准化处理 K1/K2 导出数据，覆盖订单/token/日报三类数据
输出格式: 统一 CSV

使用方式:
    # 命令行
    python data_processor.py --contract k1 --type order --date 2026-03-24 --input /path/to/raw.xlsx

    # Python 调用
    from data_processor import process_data
    process_data('k1', 'order', '2026-03-24', '/path/to/raw.xlsx')
"""

import argparse
import os
import sys
import pandas as pd
import numpy as np

# ============================================================
# 配置
# ============================================================
BASE_OUTPUT = '/Users/yy/.openclaw/workspace/db/files'
SUBDIRS = {
    'order': '订单数据',
    'token': 'token数据',
    'daily': '日报数据'
}

# ============================================================
# 默认数据路径（原始文件存放位置）
# ============================================================
# 原始文件上传到 db/files/{数据类型}/，处理脚本自动读写同一目录
# 处理完成后若用户确认无误，删除原始导出文件

# ============================================================
# 列名映射：英文 → 中文（订单数据 66→54列）
# ============================================================
ORDER_COL_MAP = {
    'time': '时间', 'block': '区块号', 'path': '交易对', 'position': '位置',
    'direction': '交易方向', 'maxpair_stable_reserve': '稳定币库存',
    'maxpair_token_reserve': 'token库存', 'token_amount': 'token变化量',
    'stable_amount': '稳定币变化量', 'stable_amount_u': '稳定币变化量u',
    'transRate': '交易占比', 'status': '状态', 'token_address': 'token地址',
    'stable_address': '稳定币地址', 'pair': '交易对地址',
    'token_decimals': 'token_decimals', 'stable_decimals': 'stable_decimals',
    'token_holding': 'token持仓_raw', 'holding_rate': '持仓占比',
    'token_value': 'token持仓价值', 'stable_holding': '稳定币持仓_raw',
    'stable_value': '稳定币持仓价值', 'last_token': 'token上笔持仓_raw',
    'last_value': 'token上笔持仓价值', 'last_stable': '稳定币上笔持仓_raw',
    'last_stable_value': '稳定币上笔持仓价值',
    'token_maxpair': 'token-w1最大交易对',
    'token_maxpair_stable_address': 'token_w1最大交易对稳定币地址',
    'reserve0': 'token最大交易对稳定币库存',
    'reserve1': 'token最大交易对token库存',
    'wbnb_price': 'WBNB价格', 'gasprice': 'gasprice',
    'wbnb_gas': 'wbnb_gas费', 'gasfee': 'gas费u', 'gaslimit': 'gaslimit',
    'wbnb_bundle': 'wbnb_bundle', 'bundle': '捆绑费',
    'single_PL': '单笔盈亏', 'totalPL': '今日交易对盈亏',
    'contract_address': '合约地址', 'pair_type': '交易对类型',
    'method': 'method', 'hash': '交易hash',
    'hold_reserve_rate': '虚拟持仓占比',
    'stable_singlePL': '单笔稳定币自增长盈亏',
    'stable_totalPL': '今日稳定币盈亏',
    'bnb_amount': 'BNB剩余持仓_raw', 'bnb_value': 'BNB剩余持仓价值',
    'last_bnb_amount': 'BNB上笔剩余持仓_raw',
    'last_bnb_value': 'BNB上笔剩余持仓价值',
    'bnb_singlePL': 'BNB单笔自增长盈亏', 'bnb_totalPL': 'BNB今日盈亏',
    'profit_virtual': '带手续费理论利润',
    'bundle_rate_fee': '带手续费捆绑比例',
    'price_diff': '价差', 'order_rate': '订单交易对手续费'
}

ORDER_DROP = [
    'id', 'hash_num',
    'w1_uw_maxpair', 'w1_reserve', 'w1_uw_reserve',
    'w2_uw_maxpair', 'w2_reserve', 'w2_uw_reserve',
    'bundle_rate', 'profit_virtual_fee'
]

# ============================================================
# Step 1: 订单数据处理
# ============================================================
def process_order_data(filepath, output_path=None):
    """
    处理订单数据（清洗版）
    输入: .xlsx (原始导出)
    输出: .csv (标准化)

    步骤:
        1. 读取 Excel（openpyxl）
        2. 列名标准化（英文→中文）
        3. 删除多余列（12列）
        4. 数据类型校正
        5. wei 单位换算
        6. 过滤成功订单（状态=1）
        7. 保存 CSV

    参数:
        filepath: 原始导出文件路径 (.xlsx)
        output_path: 输出路径（默认自动生成 .csv）

    返回:
        DataFrame
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    print(f"[订单数据] 读取: {filepath}")
    df = pd.read_excel(filepath, engine='openpyxl')
    print(f"[订单数据] 原始: {len(df)} 行, {len(df.columns)} 列")

    # Step 2: 列名标准化
    df = df.rename(columns=ORDER_COL_MAP)

    # Step 3: 删除多余列
    existing_drop = [c for c in ORDER_DROP if c in df.columns]
    df = df.drop(columns=existing_drop)
    print(f"[订单数据] 删除 {len(existing_drop)} 列，剩余 {len(df.columns)} 列")

    # Step 4: 数据类型校正
    df['时间'] = pd.to_datetime(df['时间'])
    df['区块号'] = df['区块号'].astype(int)
    df['状态'] = df['状态'].astype(int)

    # Step 5: wei 单位换算
    # BNB 持仓：除以 1e18
    for raw_col in ['BNB剩余持仓_raw', 'BNB上笔剩余持仓_raw']:
        if raw_col in df.columns:
            df[raw_col.replace('_raw', '')] = pd.to_numeric(df[raw_col], errors='coerce') / 1e18
            df.drop(columns=[raw_col], inplace=True)

    # token/stable 持仓：除以 10^decimals
    if 'token_decimals' in df.columns and 'stable_decimals' in df.columns:
        df['token_decimals'] = pd.to_numeric(df['token_decimals'], errors='coerce')
        df['stable_decimals'] = pd.to_numeric(df['stable_decimals'], errors='coerce')
        for raw_col in ['token持仓_raw', 'token上笔持仓_raw']:
            clean = raw_col.replace('_raw', '')
            if raw_col in df.columns:
                df[clean] = df[raw_col] / (10 ** df['token_decimals'])
                df.drop(columns=[raw_col], inplace=True)
        for raw_col in ['稳定币持仓_raw', '稳定币上笔持仓_raw']:
            clean = raw_col.replace('_raw', '')
            if raw_col in df.columns:
                df[clean] = df[raw_col] / (10 ** df['stable_decimals'])
                df.drop(columns=[raw_col], inplace=True)
        df.drop(columns=['token_decimals', 'stable_decimals'], inplace=True)

    print(f"[订单数据] wei换算完成，剩余 {len(df.columns)} 列")

    # Step 6: 过滤成功订单
    df_success = df[df['状态'] == 1].copy()
    print(f"[订单数据] 成功订单: {len(df_success)} / {len(df)}")

    # Step 7: 验算
    if len(df_success) > 0:
        bundle_err = abs(df_success['捆绑费'] - df_success['wbnb_bundle'] * df_success['WBNB价格']).mean()
        print(f"[订单数据] 捆绑费验算误差: {bundle_err:.6f} (应 < 0.01)")

    # Step 8: 保存 CSV
    if output_path:
        if not output_path.endswith('.csv'):
            output_path = output_path.replace('.xlsx', '.csv')
        df_success.to_csv(output_path, index=False)
        print(f"[订单数据] 保存: {output_path}")

    return df_success

# ============================================================
# Step 2: token 数据处理
# ============================================================
def process_token_data(filepath, output_path=None):
    """
    处理 token 数据
    输入: .csv 或 .xlsx
    输出: .csv (标准化)

    步骤:
        1. 读取
        2. 清理 HTML 标签
        3. 数值精度格式化
        4. 字符串去空格
        5. 保存 CSV
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    print(f"[token数据] 读取: {filepath}")
    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)
    print(f"[token数据] 原始: {len(df)} 行, {len(df.columns)} 列")

    # Step 2: 清理 HTML
    if '清空数据' in df.columns:
        df['清空数据'] = df['清空数据'].astype(str).str.replace(r'<[^>]+>', '', regex=True)
        print(f"[token数据] HTML已清理")

    # Step 3: 数值精度
    for col in ['稳库存u', '交易量', 'U类型交易量', 'BNB类型交易量']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

    # Step 4: 字符串去空格 + 清理多行值
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.replace('\n', ' ', regex=False).str.strip()

    print(f"[token数据] 格式化完成，{len(df.columns)} 列")

    # Step 5: 保存 CSV
    if output_path:
        if not output_path.endswith('.csv'):
            output_path = output_path.replace('.xlsx', '.csv')
        df.to_csv(output_path, index=False)
        print(f"[token数据] 保存: {output_path}")

    return df

# ============================================================
# Step 3: 日报数据处理
# ============================================================
def process_daily_data(filepath, date_str, output_path=None):
    """
    处理日报数据
    输入: .csv 或 .xlsx
    输出: .csv (标准化)

    步骤:
        1. 读取
        2. 插入日期列（从文件名提取）
        3. 数值精度整理
        4. 保存 CSV
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    print(f"[日报数据] 读取: {filepath}")
    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)
    print(f"[日报数据] 原始: {len(df)} 行, {len(df.columns)} 列")

    # Step 2: 插入日期列
    df.insert(0, '日期', date_str)
    print(f"[日报数据] 添加日期: {date_str}")

    # Step 3: 数值精度
    for col in df.select_dtypes(include='float64').columns:
        df[col] = df[col].round(4)

    print(f"[日报数据] 精度整理完成，{len(df.columns)} 列")

    # Step 4: 保存 CSV
    if output_path:
        if not output_path.endswith('.csv'):
            output_path = output_path.replace('.xlsx', '.csv')
        df.to_csv(output_path, index=False)
        print(f"[日报数据] 保存: {output_path}")

    return df

# ============================================================
# 统一入口
# ============================================================
def process_data(contract, data_type, date_str, input_path, output_dir=None):
    """
    统一数据处理入口

    参数:
        contract: 'k1' 或 'k2'
        data_type: 'order' / 'token' / 'daily'
        date_str: 日期 YYYY-MM-DD
        input_path: 原始文件路径 (.xlsx)
        output_dir: 输出目录（默认 db/files/{数据类型}/）

    返回:
        处理后的 DataFrame

    示例:
        df = process_data('k1', 'order', '2026-03-24', '/path/to/k1_export_orders_20260324.xlsx')
    """
    if output_dir is None:
        subdir = SUBDIRS.get(data_type, '其他')
        output_dir = os.path.join(BASE_OUTPUT, subdir)

    os.makedirs(output_dir, exist_ok=True)

    # 生成输出文件名 (.csv)
    type_name = {'order': '订单数据', 'token': 'token数据', 'daily': '日报数据'}[data_type]
    output_filename = f'{contract}_{type_name}_{date_str}.csv'
    output_path = os.path.join(output_dir, output_filename)

    # 根据类型调用
    if data_type == 'order':
        df = process_order_data(input_path, output_path)
    elif data_type == 'token':
        df = process_token_data(input_path, output_path)
    elif data_type == 'daily':
        df = process_daily_data(input_path, date_str, output_path)
    else:
        raise ValueError(f"未知数据类型: {data_type}")

    print(f"\n✅ 处理完成: {output_path} ({len(df)} 行)")
    return df

# ============================================================
# 命令行入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='标准化数据处理流水线（输出CSV）')
    parser.add_argument('--contract', required=True, choices=['k1', 'k2'])
    parser.add_argument('--type', required=True, choices=['order', 'token', 'daily'])
    parser.add_argument('--date', required=True, help='日期 YYYY-MM-DD')
    parser.add_argument('--input', required=True, help='原始文件路径')
    parser.add_argument('--output-dir', help='输出目录（可选）')
    args = parser.parse_args()

    df = process_data(
        contract=args.contract,
        data_type=args.type,
        date_str=args.date,
        input_path=args.input,
        output_dir=args.output_dir
    )
    print(f"处理完成: {len(df)} 行")
    return df

if __name__ == '__main__':
    main()
