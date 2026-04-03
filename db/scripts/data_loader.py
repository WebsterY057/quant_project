"""
数据加载脚本库
版本: v2.0 | 更新: 2026-03-27

功能: 标准化加载 db/files/ 下的数据文件（CSV格式）

命名规范:
    {合约}_{数据类别}_{日期}.csv
    合约: k1 / k2
    数据类别: 订单数据 / token数据 / 日报数据

使用方式:
    from data_loader import load_order_data, load_token_data, load_daily_data
    df = load_order_data('k1', '2026-03-24')
"""

import pandas as pd
import os

BASE_DIR = '/Users/yy/.openclaw/workspace/db/files'

# ============================================================
# 订单数据加载
# ============================================================
def load_order_data(contract='k1', date='2026-03-24'):
    """
    加载订单数据（CSV，54列标准化中文）

    参数:
        contract: 'k1' 或 'k2'
        date: 日期字符串 YYYY-MM-DD

    返回:
        DataFrame

    数据来源:
        db/files/订单数据/{contract}_订单数据_{date}.csv
    """
    filepath = os.path.join(BASE_DIR, '订单数据', f'{contract}_订单数据_{date}.csv')
    df = pd.read_csv(filepath, low_memory=False)
    return df

def load_order_data_raw(filepath):
    """
    从原始导出文件加载并清洗订单数据

    参数:
        filepath: 原始 .xlsx 文件路径

    返回:
        DataFrame（已清洗）

    处理步骤:
        1. 读取 Excel → 列名标准化 → 删除多余列
        2. 数据类型校正 → wei换算 → 过滤成功订单
    """
    from data_processor import process_order_data
    return process_order_data(filepath)

# ============================================================
# token 数据加载
# ============================================================
def load_token_data(contract='k1', date='2026-03-27'):
    """
    加载 token 数据（CSV，31列标准化）

    参数:
        contract: 'k1' 或 'k2'
        date: 日期字符串 YYYY-MM-DD

    返回:
        DataFrame

    数据来源:
        db/files/token数据/{contract}_token数据_{date}.csv
    """
    filepath = os.path.join(BASE_DIR, 'token数据', f'{contract}_token数据_{date}.csv')
    df = pd.read_csv(filepath)
    return df

# ============================================================
# 日报数据加载
# ============================================================
def load_daily_data(contract='k1', date='2026-03-26'):
    """
    加载日报数据（CSV，9列含日期）

    参数:
        contract: 'k1' 或 'k2'
        date: 日期字符串 YYYY-MM-DD

    返回:
        DataFrame

    数据来源:
        db/files/日报数据/{contract}_日报数据_{date}.csv
    """
    filepath = os.path.join(BASE_DIR, '日报数据', f'{contract}_日报数据_{date}.csv')
    df = pd.read_csv(filepath)
    return df
