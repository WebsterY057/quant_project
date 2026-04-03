"""
Alpha 分析核心公式脚本库
版本: v1.0 | 更新: 2026-03-27
来源: 基于 MEMORY.md 核心公式 + alpha_归因分析.json

使用方法:
    from core_formulas import calc_gap, calc_slippage, calc_alpha
    df = calc_gap(df)
"""

import pandas as pd
import numpy as np

# ============================================================
# 公式 1: gap（利润缺口）
# ============================================================
def calc_gap(df):
    """
    gap = 单笔盈亏 - 带手续费理论利润

    公式定义:
        gap = single_PL - profit_virtual

    数据来源:
        - 单笔盈亏: k1_订单数据_*.xlsx / 单笔盈亏
        - 带手续费理论利润: k1_订单数据_*.xlsx / 带手续费理论利润

    含义: 实际利润与理论利润的差值，正值表示跑赢理论，负值表示跑输

    使用场景: Alpha归因分析报告_k1_订单数据_2026-03-24.md
    """
    df['gap'] = df['单笔盈亏'] - df['带手续费理论利润']
    return df

# ============================================================
# 公式 2: slippage（滑点损耗）
# ============================================================
def calc_slippage(df):
    """
    slippage = gap - (-total_fee + bnb_singlePL)

    公式定义:
        slippage = (single_PL - profit_virtual) - (-(bundle + gasfee) + bnb_singlePL)

    数据来源:
        - single_PL: k1_订单数据_*.xlsx / 单笔盈亏
        - profit_virtual: k1_订单数据_*.xlsx / 带手续费理论利润
        - bundle: k1_订单数据_*.xlsx / 捆绑费
        - gasfee: k1_订单数据_*.xlsx / gas费u
        - bnb_singlePL: k1_订单数据_*.xlsx / BNB单笔自增长盈亏

    含义: 扣除理论利润和费用后，所有无法解释的收益/损失总和
          正值 = 价格朝有利方向移动（卖币触发后继续涨 / 买币触发后继续跌）
          负值 = 价格朝不利方向移动（买币触发后跌 / 卖币触发后涨）

    注意: 此为近似公式，假设 bnb_singlePL 与 slippage 可线性分离
          原公式来自 alpha_归因分析.json (L1 执行层)

    使用场景: Alpha归因分析报告_k1_订单数据_2026-03-24.md
    """
    df['total_fee'] = df['捆绑费'] + df['gas费u']
    df['gap'] = df['单笔盈亏'] - df['带手续费理论利润']
    df['slippage'] = df['gap'] - (-df['total_fee'] + df['BNB单笔自增长盈亏'])
    return df

# ============================================================
# 公式 3: alpha（净 Alpha）
# ============================================================
def calc_alpha(df):
    """
    alpha = slippage + total_fee

    公式定义:
        alpha = (single_PL - profit_virtual - (-(bundle+gasfee) + bnb_singlePL)) + (bundle + gasfee)

    简化后:
        alpha = single_PL - profit_virtual + bnb_singlePL

    数据来源:
        - single_PL: 单笔盈亏
        - profit_virtual: 带手续费理论利润
        - bnb_singlePL: BNB单笔自增长盈亏

    含义: 策略相对于理论基准的超额收益
          alpha > 0 表示策略跑赢理论预期

    使用场景: MEMORY.md 核心公式定义
    """
    df['total_fee'] = df['捆绑费'] + df['gas费u']
    df['slippage'] = calc_slippage(df)['slippage']  # 避免重复赋值
    df['alpha'] = df['slippage'] + df['total_fee']
    return df

# ============================================================
# 公式 4: 理论利润验算
# ============================================================
def verify_profit_virtual(df):
    """
    验算: 带手续费理论利润 ≈ |稳定币变化量u| × 价差 × (1 - 带手续费捆绑比例)

    数据来源:
        - 带手续费理论利润: k1_订单数据_*.xlsx / 带手续费理论利润
        - 稳定币变化量u: k1_订单数据_*.xlsx / 稳定币变化量u
        - 价差: k1_订单数据_*.xlsx / 价差
        - 带手续费捆绑比例: k1_订单数据_*.xlsx / 带手续费捆绑比例

    返回: 验算误差均值
    """
    expected = abs(df['稳定币变化量u']) * df['价差'] * (1 - df['带手续费捆绑比例'])
    error = abs(df['带手续费理论利润'] - expected).mean()
    return error

# ============================================================
# 公式 5: 捆绑费验算
# ============================================================
def verify_bundle(df):
    """
    验算: 捆绑费 ≈ wbnb_bundle × WBNB价格

    数据来源:
        - 捆绑费: k1_订单数据_*.xlsx / 捆绑费
        - wbnb_bundle: k1_订单数据_*.xlsx / wbnb_bundle
        - WBNB价格: k1_订单数据_*.xlsx / WBNB价格

    返回: 验算误差均值
    """
    expected = df['wbnb_bundle'] * df['WBNB价格']
    error = abs(df['捆绑费'] - expected).mean()
    return error

# ============================================================
# 公式 6: 费用率
# ============================================================
def calc_fee_rate(df):
    """
    费用率 = 捆绑费 / 带手续费理论利润

    数据来源:
        - 捆绑费: k1_订单数据_*.xlsx / 捆绑费
        - 带手续费理论利润: k1_订单数据_*.xlsx / 带手续费理论利润

    含义: 理论利润中被捆绑费侵蚀的比例
    """
    df['费用率'] = df['捆绑费'] / df['带手续费理论利润'].replace(0, np.nan)
    return df

# ============================================================
# 公式 7: 单笔盈亏验证
# ============================================================
def verify_single_pl(df):
    """
    验算: 单笔盈亏 ≈ token持仓价值变化 + 稳定币变化量u - 捆绑费 - gas费

    公式:
        single_PL ≈ (token_value - last_value) + stable_amount_u - bundle - gasfee

    数据来源:
        - 单笔盈亏: k1_订单数据_*.xlsx / 单笔盈亏
        - token持仓价值: k1_订单数据_*.xlsx / token持仓价值
        - last_value: k1_订单数据_*.xlsx / token上笔持仓价值
        - stable_amount_u: k1_订单数据_*.xlsx / 稳定币变化量u
        - 捆绑费: k1_订单数据_*.xlsx / 捆绑费
        - gasfee: k1_订单数据_*.xlsx / gas费u

    返回: 验算误差均值
    """
    expected = (df['token持仓价值'] - df['token上笔持仓价值']) + df['稳定币变化量u'] - df['捆绑费'] - df['gas费u']
    error = abs(df['单笔盈亏'] - expected).mean()
    return error
