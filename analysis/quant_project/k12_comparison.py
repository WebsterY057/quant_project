#!/usr/bin/env python3
"""K12 comparison analysis: 我们K12 vs 龟K12 (2026-03-27)"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. LOAD DATA
# ============================================================
print("Loading data...")

our = pd.read_csv('/Users/yy/.openclaw/workspace/db/files/汇总/我们K12_合并订单_2026-03-27.csv')
turtle = pd.read_csv('/Users/yy/.openclaw/workspace/db/files/汇总/龟K12_合并订单_2026-03-27.csv')
our_token = pd.read_csv('/Users/yy/.openclaw/workspace/db/files/汇总/我们K12_Token汇总_2026-03-27.csv')
turtle_token = pd.read_csv('/Users/yy/.openclaw/workspace/db/files/汇总/龟K12_Token汇总_2026-03-27.csv')

print(f"我们K12 rows: {len(our)}, columns: {list(our.columns)}")
print(f"龟K12 rows: {len(turtle)}, columns: {list(turtle.columns)}")

# ============================================================
# 2. PREPARE OUR DATA
# ============================================================
# abs_stable already exists in our data
our['abs_stable'] = our['abs_stable'].fillna(0)

# total_fee = 捆绑费 + gas费
our['total_fee'] = our['捆绑费'].fillna(0) + our['gas费u'].fillna(0)

# Alpha formula: alpha = 单笔盈亏 - 理论利润 - BNB自增长
our['alpha_calc'] = our['单笔盈亏'] - our['带手续费理论利润'].fillna(0) - our['BNB单笔自增长盈亏'].fillna(0)

# Slippage = alpha + total_fee
our['slip'] = our['alpha_calc'] + our['total_fee']

# Extract source (K1/K2) - must be AFTER slip is computed
our['src'] = our['来源'].map({'k1': 'K1', 'k2': 'K2'})
our_k1 = our[our['src'] == 'K1']
our_k2 = our[our['src'] == 'K2']

# abs_stable for turtle
turtle['abs_stable'] = turtle['稳定币变化量u'].abs()
turtle['total_fee'] = turtle['捆绑费'].fillna(0) + turtle['gas费u'].fillna(0)

# Alpha for turtle: 单笔盈亏 - 理论利润基准 - BNB
turtle['alpha_calc'] = turtle['单笔盈亏'] - turtle['理论利润基准'].fillna(0) - turtle['BNB单笔自增长盈亏'].fillna(0)
turtle['slip'] = turtle['alpha_calc'] + turtle['total_fee']

# src
turtle['src'] = turtle['来源'].map({'k1': 'K1', 'k2': 'K2'})
turtle_k1 = turtle[turtle['src'] == 'K1']
turtle_k2 = turtle[turtle['src'] == 'K2']

print("Data loaded and prepared.")

# ============================================================
# 3. FIVE-METRIC SUMMARY
# ============================================================
def five_metrics(df, label):
    pnl = df['单笔盈亏'].sum()
    cnt = len(df)
    vol = df['abs_stable'].sum()
    gas = df['gas费u'].sum()
    bundle = df['捆绑费'].sum()
    theor = df['带手续费理论利润'].fillna(0).sum() if '带手续费理论利润' in df.columns else 0
    theor_t = df['理论利润基准'].fillna(0).sum() if '理论利润基准' in df.columns else 0
    theor_use = theor if theor != 0 else theor_t
    alpha_sum = df['alpha_calc'].sum() if 'alpha_calc' in df.columns else 0
    slip_sum = df['slip'].sum() if 'slip' in df.columns else 0
    bnb_pnl = df['BNB单笔自增长盈亏'].fillna(0).sum() if 'BNB单笔自增长盈亏' in df.columns else 0
    bundle_rate = bundle / theor_use if theor_use != 0 else 0
    avg_gas = gas / cnt if cnt > 0 else 0
    avg_bundle = bundle / cnt if cnt > 0 else 0
    print(f"\n{label}:")
    print(f"  单笔盈亏_sum={pnl:.2f}, 笔数={cnt}, 成交量={vol:.2f}, gas费={gas:.2f}, 捆绑费={bundle:.2f}")
    print(f"  理论利润={theor_use:.2f}, Alpha={alpha_sum:.2f}, Slip={slip_sum:.2f}")
    print(f"  BNB_pnl={bnb_pnl:.2f}, 捆绑费率={bundle_rate:.4f}, 均笔gas={avg_gas:.4f}, 均笔捆绑={avg_bundle:.4f}")
    return {
        'label': label,
        '单笔盈亏': pnl,
        '笔数': cnt,
        '成交量': vol,
        'gas费': gas,
        '捆绑费': bundle,
        '理论利润': theor_use,
        'Alpha': alpha_sum,
        'Slip': slip_sum,
        'BNB': bnb_pnl,
        '捆绑费率': bundle_rate,
        '均笔gas': avg_gas,
        '均笔捆绑费': avg_bundle,
    }

m_our_k1 = five_metrics(our_k1, "我们K1")
m_our_k2 = five_metrics(our_k2, "我们K2")
m_our_k12 = five_metrics(our, "我们K12")
m_turtle_k1 = five_metrics(turtle_k1, "龟K1")
m_turtle_k2 = five_metrics(turtle_k2, "龟K2")
m_turtle_k12 = five_metrics(turtle, "龟K12")

# ============================================================
# 4. FILTERING ANALYSIS
# ============================================================
print("\n\n=== FILTERING ANALYSIS ===")
# For our data: check what pairs were filtered
# Filtered pairs are those with 状态 != 1 or other criteria
our_filtered = our[our['状态'] != 1]
print(f"我们 状态!=1 订单: {len(our_filtered)}")
print(f"状态分布: {our['状态'].value_counts().to_dict()}")

# ============================================================
# 5. SIZE INTERVAL ANALYSIS
# ============================================================
print("\n\n=== SIZE INTERVAL ANALYSIS ===")
bins = [0, 50, 100, 500, 1000, 5000, np.inf]
labels = ['0~50', '50~100', '100~500', '500~1k', '1k~5k', '>5k']

our['size_bin'] = pd.cut(our['abs_stable'], bins=bins, labels=labels, right=False)
turtle['size_bin'] = pd.cut(turtle['abs_stable'], bins=bins, labels=labels, right=False)

size_our = our.groupby('size_bin', observed=True).agg(
    笔数=('slip', 'count'),
    slip累计=('slip', 'sum'),
    slip均值=('slip', 'mean'),
    单笔盈亏均值=('单笔盈亏', 'mean')
).reset_index()

size_turtle = turtle.groupby('size_bin', observed=True).agg(
    笔数=('slip', 'count'),
    slip累计=('slip', 'sum'),
    slip均值=('slip', 'mean'),
    单笔盈亏均值=('单笔盈亏', 'mean')
).reset_index()

print("\n我们K12 规模区间:")
print(size_our.to_string())
print("\n龟K12 规模区间:")
print(size_turtle.to_string())

# ============================================================
# 6. BUY/SELL DIRECTION ANALYSIS
# ============================================================
print("\n\n=== BUY/SELL DIRECTION ===")
def direction_stats(df, label):
    buy = df[df['交易方向'] == '买币']
    sell = df[df['交易方向'] == '卖币']
    results = {}
    for name, sub in [('买币', buy), ('卖币', sell)]:
        cnt = len(sub)
        slip_sum = sub['slip'].sum()
        slip_avg = slip_sum / cnt if cnt > 0 else 0
        pnl_avg = sub['单笔盈亏'].mean() if cnt > 0 else 0
        bundle = sub['捆绑费'].sum()
        gas = sub['gas费u'].sum()
        tf = sub['total_fee'].sum()
        print(f"{label} {name}: 笔数={cnt}, slip_sum={slip_sum:.2f}, slip_avg={slip_avg:.4f}, pnl_avg={pnl_avg:.4f}, bundle={bundle:.2f}, gas={gas:.2f}, total_fee={tf:.2f}")
        results[name] = {'笔数': cnt, 'slip_sum': slip_sum, 'slip_avg': slip_avg, 'pnl_avg': pnl_avg, 'bundle': bundle, 'gas': gas, 'total_fee': tf}
    return results

dir_our = direction_stats(our, "我们K12")
dir_turtle = direction_stats(turtle, "龟K12")

# ============================================================
# 7. TOKEN-LEVEL ANALYSIS
# ============================================================
print("\n\n=== TOKEN-LEVEL ANALYSIS ===")

# Key tokens: C, ARIA, SIREN, Beat, CYS
key_tokens = ['C', 'ARIA', 'SIREN', 'Beat', 'CYS']

print("\n我们K1/K2 分Token对比:")
for tok in key_tokens:
    k1 = our_k1[our_k1['base'] == tok]
    k2 = our_k2[our_k2['base'] == tok]
    k12 = our[our['base'] == tok]
    k1_slip = k1['slip'].sum()
    k2_slip = k2['slip'].sum()
    k12_slip = k12['slip'].sum()
    print(f"  {tok}: K1笔数={len(k1)}, slip={k1_slip:.2f} | K2笔数={len(k2)}, slip={k2_slip:.2f} | K12笔数={len(k12)}, slip={k12_slip:.2f}")

# Our exclusive tokens
our_tokens = set(our['base'].dropna().unique())
turtle_addrs = set(turtle_token['交易对'].unique() if '交易对' in turtle_token.columns else [])

# Map our tokens to addresses for comparison
our_addr_map = our.drop_duplicates(subset='token地址')[['base', 'token地址']].dropna()
our_addr_dict = dict(zip(our_addr_map['base'], our_addr_map['token地址']))

our_exclusive = []
for tok in our_tokens:
    addr = our_addr_dict.get(tok, '')
    if addr not in turtle_addrs:
        sub = our[our['base'] == tok]
        slip = sub['slip'].sum()
        cnt = len(sub)
        slip_per = slip / cnt if cnt > 0 else 0
        our_exclusive.append({'token': tok, '地址': addr, '笔数': cnt, 'slip': slip, 'slip_per': slip_per})

our_excl_df = pd.DataFrame(our_exclusive).sort_values('slip', ascending=True)
print("\n我们独有Token (slip最差5个):")
print(our_excl_df.head(5).to_string())

# Turtle exclusive tokens
turtle_tokens_in_data = set(turtle['交易对'].dropna().unique())
our_addrs_in_data = set(our['token地址'].dropna().unique())

turtle_exclusive = []
for addr in turtle_tokens_in_data:
    if addr not in our_addrs_in_data:
        sub = turtle[turtle['交易对'] == addr]
        slip = sub['slip'].sum()
        cnt = len(sub)
        slip_per = slip / cnt if cnt > 0 else 0
        turtle_exclusive.append({'地址': addr, '笔数': cnt, 'slip': slip, 'slip_per': slip_per})

turtle_excl_df = pd.DataFrame(turtle_exclusive).sort_values('slip', ascending=False)
print("\n龟独有Token (slip最好5个):")
print(turtle_excl_df.head(5).to_string())

# ============================================================
# 8. BLACKLIST RECOMMENDATIONS
# ============================================================
print("\n\n=== BLACKLIST RECOMMENDATIONS ===")
our_token_stats = our.groupby('base').agg(
    笔数=('slip', 'count'),
    slip=('slip', 'sum'),
    单笔盈亏=('单笔盈亏', 'sum')
).reset_index()
our_token_stats['slip_per'] = our_token_stats['slip'] / our_token_stats['笔数']

# Condition 1: K12 slip < -500 U AND slip_per < -0.3 U
cond1 = our_token_stats[(our_token_stats['slip'] < -500) & (our_token_stats['slip_per'] < -0.3)]
# Condition 2: 单笔盈亏 < 0 AND slip < 0
our_token_stats2 = our.groupby('base').agg(
    pnl_sum=('单笔盈亏', 'sum'),
    slip_sum=('slip', 'sum')
).reset_index()
cond2_base = our_token_stats2[(our_token_stats2['pnl_sum'] < 0) & (our_token_stats2['slip_sum'] < 0)]['base'].tolist()

blacklist = pd.concat([cond1, our_token_stats[our_token_stats['base'].isin(cond2_base)] if len(cond2_base) > 0 else pd.DataFrame()]).drop_duplicates()
print(f"建议拉黑Token ({len(blacklist)}个):")
print(blacklist.to_string())

# ============================================================
# 9. WORST RATIO TOKENS (Slippage vs 理论利润)
# ============================================================
print("\n\n=== WORST RATIO TOKENS ===")
our_token_ratio = our.groupby('base').agg(
    theor=('带手续费理论利润', 'sum'),
    slip=('slip', 'sum'),
    pnl=('单笔盈亏', 'sum')
).reset_index()
our_token_ratio['ratio'] = our_token_ratio['slip'] / our_token_ratio['theor'].abs().replace(0, np.nan)
worst_ratio = our_token_ratio.sort_values('ratio', ascending=True).head(10)
print("Slippage/理论利润 最差10个:")
print(worst_ratio.to_string())

# ============================================================
# 10. BNB ANALYSIS
# ============================================================
print("\n\n=== BNB ANALYSIS ===")
bnb_our = our['BNB单笔自增长盈亏'].fillna(0).sum()
bnb_turtle = turtle['BNB单笔自增长盈亏'].fillna(0).sum()
print(f"我们K12 BNB自增长盈亏: {bnb_our:.2f}")
print(f"龟K12 BNB自增长盈亏: {bnb_turtle:.2f}")

print("\n\n=== ALL DONE ===")
