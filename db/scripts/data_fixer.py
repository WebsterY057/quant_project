"""
数据修复脚本
版本: v1.0 | 更新: 2026-03-27

功能: 修复已处理但格式不正确的文件

处理 db/files/ 下的所有标准化数据，修正字段格式问题
"""

import pandas as pd
import numpy as np
import os

BASE = '/Users/yy/.openclaw/workspace/db/files'

# ============================================================
# 修复 1: 订单数据 — wei 换算 + 类型校正
# ============================================================
def fix_order_data(filepath):
    """
    订单数据格式问题：
    - wei 列为 object 类型（字符串），需转为 float 并换算
    - token/stable decimals 列可能仍存在
    """
    print(f"\n修复订单数据: {filepath}")
    df = pd.read_excel(filepath, engine='openpyxl')
    print(f"  原始: {len(df)} 行, {len(df.columns)} 列")

    # 确认问题列
    wei_cols = ['token持仓', '稳定币持仓', 'BNB剩余持仓', 'BNB上笔剩余持仓']
    for col in wei_cols:
        if col in df.columns:
            sample = df[col].dropna().iloc[0] if df[col].dropna().shape[0] > 0 else None
            if sample is not None:
                try:
                    val = float(sample)
                    print(f"  {col}: dtype={df[col].dtype}, sample={val:.2e}, 需换算={val > 1e10}")
                except (ValueError, TypeError):
                    print(f"  {col}: dtype={df[col].dtype}, sample={sample}, 无法解析")

    # 获取 decimals（默认 18，如果列不存在或值为 NaN）
    decimals_token = df['token_decimals'].iloc[0] if 'token_decimals' in df.columns and len(df) > 0 else 18
    decimals_stable = df['stable_decimals'].iloc[0] if 'stable_decimals' in df.columns and len(df) > 0 else 18
    if pd.isna(decimals_token):
        decimals_token = 18
        print(f"  token_decimals 为 NaN，使用默认值 18")
    if pd.isna(decimals_stable):
        decimals_stable = 18
        print(f"  stable_decimals 为 NaN，使用默认值 18")
    if 'token_decimals' not in df.columns:
        print(f"  token_decimals 不在列中，使用默认值 {decimals_token}")
    if 'stable_decimals' not in df.columns:
        print(f"  stable_decimals 不在列中，使用默认值 {decimals_stable}")

    # wei 换算
    for col in wei_cols:
        if col in df.columns and df[col].dtype == 'object':
            # 先转 float
            df[col] = pd.to_numeric(df[col], errors='coerce')
            print(f"  {col} 已转为 float")

    # BNB: 除以 1e18
    for col in ['BNB剩余持仓', 'BNB上笔剩余持仓']:
        if col in df.columns:
            max_val = df[col].max()
            if max_val > 1e10:
                df[col] = df[col] / 1e18
                print(f"  {col} 已除以 1e18，max={df[col].max():.4f}")

    # token/stable: 除以 10^decimals
    print(f"  token_decimals={decimals_token}, stable_decimals={decimals_stable}")

    for col in ['token持仓', 'token上笔持仓']:
        if col in df.columns:
            max_val = df[col].max()
            if max_val > 1e10:
                df[col] = df[col] / (10 ** decimals_token)
                print(f"  {col} 已除以 10^{decimals_token}，max={df[col].max():.4f}")

    for col in ['稳定币持仓', '稳定币上笔持仓']:
        if col in df.columns:
            max_val = df[col].max()
            if max_val > 1e10:
                df[col] = df[col] / (10 ** decimals_stable)
                print(f"  {col} 已除以 10^{decimals_stable}，max={df[col].max():.4f}")

    # 删除 decimals 列
    for col in ['token_decimals', 'stable_decimals']:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)
            print(f"  删除 {col}")

    print(f"  修复后: {len(df.columns)} 列")
    return df

# ============================================================
# 修复 2: token 数据 — 格式清洗
# ============================================================
def fix_token_data(filepath):
    """
    token数据格式问题：
    - 成功率/胜率/当日非首位订单率 含百分号或括号格式
    - 清空数据含 NaN 或 HTML 标签
    - 多行值含 \n
    - 数值精度不足
    """
    print(f"\n修复 token 数据: {filepath}")
    df = pd.read_excel(filepath, engine='openpyxl')
    print(f"  原始: {len(df)} 行, {len(df.columns)} 列")

    # 成功率：去除百分号
    if '成功率' in df.columns:
        if df['成功率'].dtype == 'object':
            df['成功率'] = df['成功率'].str.rstrip('%')
            df['成功率'] = pd.to_numeric(df['成功率'], errors='coerce')
            print(f"  成功率 已转为 float")

    # 胜率：从 "1969 (42.44%)" 提取百分比
    if '胜率' in df.columns:
        if df['胜率'].dtype == 'object':
            df['胜率_clean'] = df['胜率'].str.extract(r'\((\d+\.?\d*)%\)')[0]
            df['胜率_clean'] = pd.to_numeric(df['胜率_clean'], errors='coerce')
            df.drop(columns=['胜率'], inplace=True)
            df.rename(columns={'胜率_clean': '胜率'}, inplace=True)
            print(f"  胜率 已从括号格式提取数值")

    # 当日非首位订单率：去除百分号
    if '当日非首位订单率' in df.columns:
        if df['当日非首位订单率'].dtype == 'object':
            df['当日非首位订单率'] = df['当日非首位订单率'].str.rstrip('%')
            df['当日非首位订单率'] = pd.to_numeric(df['当日非首位订单率'], errors='coerce')
            print(f"  当日非首位订单率 已转为 float")

    # 清空数据：清理 HTML + 去除 NaN
    if '清空数据' in df.columns:
        df['清空数据'] = df['清空数据'].astype(str).str.replace(r'<[^>]+>', '', regex=True)
        df['清空数据'] = df['清空数据'].replace('nan', '')
        print(f"  清空数据 已清理 HTML")

    # 多行值清理：所有字符串列去 \n
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].astype(str).str.replace('\n', ' ', regex=False).str.strip()

    # 数值精度：2位小数
    for col in ['稳库存u', '交易量', 'U类型交易量', 'BNB类型交易量']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

    print(f"  修复后: {len(df.columns)} 列")
    return df

# ============================================================
# 修复 3: 日报数据 — 精度整理
# ============================================================
def fix_daily_data(filepath):
    """
    日报数据格式问题：
    - 胜率含百分号
    - 数值精度不统一
    """
    print(f"\n修复日报数据: {filepath}")
    df = pd.read_excel(filepath, engine='openpyxl')
    print(f"  原始: {len(df)} 行, {len(df.columns)} 列")

    # 胜率：去除百分号
    if '胜率' in df.columns:
        if df['胜率'].dtype == 'object':
            df['胜率'] = df['胜率'].str.rstrip('%')
            df['胜率'] = pd.to_numeric(df['胜率'], errors='coerce')
            print(f"  胜率 已转为 float")

    # 数值精度
    for col in df.select_dtypes(include='float64').columns:
        df[col] = df[col].round(4)

    print(f"  修复后: {len(df.columns)} 列")
    return df

# ============================================================
# 主函数
# ============================================================
def fix_all():
    files = {
        '订单数据': {
            'files': [
                '/订单数据/k1_订单数据_2026-03-24.xlsx',
                '/订单数据/k2_订单数据_2026-03-24.xlsx',
            ],
            'fixer': fix_order_data
        },
        'token数据': {
            'files': [
                '/token数据/k1_token数据_2026-03-27.xlsx',
                '/token数据/k2_token数据_2026-03-27.xlsx',
            ],
            'fixer': fix_token_data
        },
        '日报数据': {
            'files': [
                '/日报数据/k1_日报数据_2026-03-26.xlsx',
            ],
            'fixer': fix_daily_data
        }
    }

    for category, info in files.items():
        for filepath in info['files']:
            full_path = BASE + filepath
            if not os.path.exists(full_path):
                print(f"\n⏭️ 跳过（文件不存在）: {full_path}")
                continue
            try:
                df_fixed = info['fixer'](full_path)
                # 保存
                df_fixed.to_excel(full_path, index=False)
                print(f"  ✅ 已保存: {full_path}")
            except Exception as e:
                print(f"  ❌ 失败: {e}")

if __name__ == '__main__':
    fix_all()
