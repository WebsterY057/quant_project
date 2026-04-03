---
name: statistical-analysis
description: "Statistical analysis for Python data analysis using scipy and statsmodels. Use when user asks for hypothesis testing, confidence intervals, regression analysis, statistical significance, p-value, t-test, ANOVA, correlation analysis."
---

# Statistical Analysis

## Quick Start

```python
import scipy.stats as stats
import statsmodels.api as sm
import numpy as np

# 基本统计量
mean = np.mean(data)
std = np.std(data)
median = np.median(data)
```

## Common Tests

### 1. T检验 (T-test)

#### 单样本t检验
```python
# 检验数据均值是否等于已知值
t_stat, p_value = stats.ttest_1samp(data, popmean=0)
```

#### 独立样本t检验
```python
# 检验两组独立样本均值是否相等
t_stat, p_value = stats.ttest_ind(group1, group2)
```

#### 配对样本t检验
```python
# 检验配对样本均值差异
t_stat, p_value = stats.ttest_rel(before, after)
```

### 2. ANOVA (方差分析)

```python
# 检验多组样本均值是否相等
f_stat, p_value = stats.f_oneway(group1, group2, group3)
```

### 3. 卡方检验 (Chi-square)

```python
# 检验分类变量独立性
chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
```

### 4. 相关性检验

```python
# Pearson相关系数
corr, p_value = stats.pearsonr(x, y)

# Spearman相关系数
corr, p_value = stats.spearmanr(x, y)

# Kendall相关系数
corr, p_value = stats.kendalltau(x, y)
```

## 回归分析

### 1. 简单线性回归

```python
# 使用 scipy
slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

# 使用 statsmodels（更详细）
X = sm.add_constant(x)  # 添加截距项
model = sm.OLS(y, X)
results = model.fit()
print(results.summary())
```

### 2. 多元线性回归

```python
X = df[['x1', 'x2', 'x3']]
X = sm.add_constant(X)
y = df['y']

model = sm.OLS(y, X)
results = model.fit()
print(results.summary())

# 系数
print(results.params)
# p值
print(results.pvalues)
# R²
print(results.rsquared)
```

### 3. Logistic回归

```python
X = sm.add_constant(df[['x1', 'x2']])
y = df['binary_outcome']

model = sm.Logit(y, X)
results = model.fit()
print(results.summary())
```

## 置信区间

### 1. 均值的置信区间

```python
from scipy.stats import t, sem

n = len(data)
mean = np.mean(data)
se = sem(data)
confidence = 0.95
ci = t.interval(confidence, n-1, loc=mean, scale=se)
print(f"95% CI: {ci}")
```

### 2. 相关系数的置信区间

```python
# Fisher z变换
z = np.arctanh(r)
se = 1/np.sqrt(n-3)
ci_low = np.tanh(z - 1.96*se)
ci_high = np.tanh(z + 1.96*se)
print(f"95% CI: [{ci_low}, {ci_high}]")
```

## 分布检验

### 1. 正态性检验

```python
# Shapiro-Wilk 检验
stat, p_value = stats.shapiro(data)

# D'Agostino-Pearson 检验
stat, p_value = stats.normaltest(data)

# Kolmogorov-Smirnov 检验
stat, p_value = stats.kstest(data, 'norm')
```

### 2. 方差齐性检验

```python
# Levene 检验
stat, p_value = stats.levene(group1, group2)

# Bartlett 检验
stat, p_value = stats.bartlett(group1, group2)
```

## 非参数检验

### 1. Mann-Whitney U 检验

```python
# 非独立样本的Wilcoxon秩和检验
stat, p_value = stats.mannwhitneyu(group1, group2)
```

### 2. Wilcoxon 符号秩检验

```python
# 配对样本的非参数检验
stat, p_value = stats.wilcoxon(before, after)
```

### 3. Kruskal-Wallis 检验

```python
# 非独立样本的方差分析
stat, p_value = stats.kruskal(group1, group2, group3)
```

## 效应量 (Effect Size)

### 1. Cohen's d

```python
def cohens_d(group1, group2):
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    return (np.mean(group1) - np.mean(group2)) / pooled_std
```

### 2. Eta-squared (η²)

```python
# 用于 ANOVA 的效应量
def eta_squared(f_stat, df_between, df_within):
    return (f_stat * df_between) / (f_stat * df_between + df_within)
```

## 结果解读

### P值解读

| P值 | 结论 |
|-----|------|
| p < 0.001 | 极显著差异 |
| p < 0.01 | 非常显著差异 |
| p < 0.05 | 显著差异 |
| p >= 0.05 | 无显著差异 |

### 效应量解读 (Cohen's d)

| 值 | 效应大小 |
|-----|---------|
| 0.2 | 小效应 |
| 0.5 | 中等效应 |
| 0.8 | 大效应 |
