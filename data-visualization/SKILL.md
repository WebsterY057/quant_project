---
name: data-visualization
description: "Data visualization for Python data analysis using matplotlib and seaborn. Use when user asks to generate charts, plots, heatmaps, or visual reports. Triggers on: generate chart, plot, visualize, matplotlib, seaborn."
---

# Data Visualization

## Quick Start

```python
import matplotlib.pyplot as plt
import seaborn as sns

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 基本折线图
plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('标题')
plt.xlabel('X轴')
plt.ylabel('Y轴')
plt.grid(True)
plt.show()
```

## Common Patterns

### 1. 散点图 (Scatter Plot)
```python
plt.figure(figsize=(10, 6))
plt.scatter(df['x'], df['y'], alpha=0.5)
plt.title('散点图示例')
plt.xlabel('X')
plt.ylabel('Y')
plt.show()
```

### 2. 柱状图 (Bar Chart)
```python
plt.figure(figsize=(10, 6))
bars = plt.bar(df['category'], df['value'])
plt.title('柱状图示例')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

### 3. 箱线图 (Box Plot)
```python
plt.figure(figsize=(10, 6))
df.boxplot(column='value', by='category')
plt.title('箱线图示例')
plt.suptitle('')  # 移除自动生成的标题
plt.show()
```

### 4. 热力图 (Heatmap)
```python
plt.figure(figsize=(12, 8))
corr = df.corr()
sns.heatmap(corr, annot=True, cmap='coolwarm', center=0)
plt.title('热力图示例')
plt.show()
```

### 5. 多子图 (Subplots)
```python
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

axes[0, 0].plot(x, y1)
axes[0, 0].set_title('子图1')

axes[0, 1].scatter(x, y2)
axes[0, 1].set_title('子图2')

axes[1, 0].bar(x, y3)
axes[1, 0].set_title('子图3')

axes[1, 1].hist(z, bins=20)
axes[1, 1].set_title('子图4')

plt.tight_layout()
plt.show()
```

## Seaborn 高级图表

### 6. 带回归线的散点图
```python
plt.figure(figsize=(10, 6))
sns.regplot(x='x', y='y', data=df)
plt.title('回归图')
plt.show()
```

### 7. 分组柱状图
```python
plt.figure(figsize=(12, 6))
sns.barplot(x='category', y='value', hue='group', data=df)
plt.title('分组柱状图')
plt.show()
```

### 8. 密度图
```python
plt.figure(figsize=(10, 6))
sns.kdeplot(df['value'], fill=True)
plt.title('密度图')
plt.show()
```

## 保存图表

```python
# 保存为 PNG
plt.savefig('chart.png', dpi=300, bbox_inches='tight')

# 保存为 PDF（矢量图）
plt.savefig('chart.pdf', bbox_inches='tight')

# 保存为 SVG（可编辑矢量图）
plt.savefig('chart.svg', bbox_inches='tight')
```

## 样式设置

```python
# 使用 seaborn 主题
sns.set_style("whitegrid")
sns.set_palette("husl")

# 设置图表大小
plt.figure(figsize=(14, 8))

# 设置刻度旋转
plt.xticks(rotation=45, ha='right')

# 设置图例位置
plt.legend(loc='upper right')
```

## 常见问题

1. **中文显示问题**：使用 `plt.rcParams['font.sans-serif']` 设置中文字体
2. **负号显示**：使用 `plt.rcParams['axes.unicode_minus'] = False`
3. **图表模糊**：使用 `dpi=300` 或更高分辨率保存
4. **布局混乱**：使用 `plt.tight_layout()`
