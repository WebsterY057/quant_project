---
name: jupyter-optimization
description: "Optimize Jupyter notebook workflow for large data analysis. Use when reading large Excel/CSV files is slow or times out, processing large datasets, or memory issues occur."
---

# Jupyter Optimization

## 1. 快速读取大文件

### CSV 文件

```python
# 方法1：只读取需要的列
df = pd.read_csv('file.csv', usecols=['col1', 'col2', 'col3'])

# 方法2：指定 dtype 减少内存
dtype_dict = {'col1': 'int32', 'col2': 'float32'}
df = pd.read_csv('file.csv', dtype=dtype_dict)

# 方法3：分块读取
chunks = pd.read_csv('file.csv', chunksize=10000)
for chunk in chunks:
    # 处理每一块
    process(chunk)

# 方法4：使用 chunksize 计算统计量
result = pd.read_csv('file.csv', chunksize=5000)['column'].mean()
```

### Excel 文件

```python
# 方法1：使用 openpyxl 引擎并设置只读
df = pd.read_excel('file.xlsx', engine='openpyxl', nrows=1000)  # 先读少量预览

# 方法2：使用 xlrd 引擎（.xls）
df = pd.read_excel('file.xls', engine='xlrd')

# 方法3：分块读取 Excel
import openpyxl
wb = openpyxl.load_workbook('file.xlsx', read_only=True)
for sheet in wb:
    for row in sheet.iter_rows(values_only=True):
        process(row)
```

## 2. 内存优化

### 检查内存使用

```python
# 查看 DataFrame 内存使用
df.info(memory_usage='deep')

# 查看每列内存
df.memory_usage(deep=True)
```

### 减少内存

```python
# 转换数据类型
df['int_col'] = pd.to_numeric(df['int_col'], downcast='integer')
df['float_col'] = pd.to_numeric(df['float_col'], downcast='float')

# 使用 category 类型（适合低基数字符串）
df['string_col'] = df['string_col'].astype('category')

# 删除不需要的列
df.drop(['col1', 'col2'], axis=1, inplace=True)

# 使用更轻量的索引
df.set_index('id', inplace=True)
```

### 释放内存

```python
import gc

# 删除大变量
del large_dataframe

# 强制垃圾回收
gc.collect()
```

## 3. 处理超时

### 使用后台执行

```python
import subprocess
import time

# 启动后台进程
proc = subprocess.Popen(['python', 'long_running_script.py'], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)

# 等待结果，设置超时
try:
    stdout, stderr = proc.communicate(timeout=300)  # 5分钟超时
except subprocess.TimeoutExpired:
    proc.kill()
    print("Process killed due to timeout")
```

### 分步执行

```python
# 将大任务分成小步骤
# 每步保存中间结果

# Step 1: 读取数据
df = pd.read_csv('data.csv')
df.to_pickle('step1.pkl')

# Step 2: 数据清洗
df = pd.read_pickle('step1.pkl')
df_clean = clean(df)
df_clean.to_pickle('step2.pkl')

# Step 3: 分析
df = pd.read_pickle('step2.pkl')
result = analyze(df)
```

## 4. 加速计算

### 向量化操作

```python
# 避免循环，使用向量化
df['new_col'] = df['col1'] * df['col2'] + df['col3']

# 使用 numpy 函数
df['new_col'] = np.where(df['condition'], value_if_true, value_if_false)
```

### 使用 apply 优化

```python
# 使用 axis=1 时避免
df['new_col'] = df.apply(lambda row: complex_func(row), axis=1)

# 改用向量化
df['new_col'] = vectorized_func(df['col1'], df['col2'])
```

### 并行处理

```python
from multiprocessing import Pool

def process_chunk(chunk):
    return chunk['col'].sum()

chunks = [chunk1, chunk2, chunk3]
with Pool(4) as p:
    results = p.map(process_chunk, chunks)
```

## 5. 保存中间结果

### 使用 pickle

```python
# 保存
df.to_pickle('df.pkl')

# 读取
df = pd.read_pickle('df.pkl')
```

### 使用 feather（快速）

```python
# 保存（需要 pyarrow）
df.to_feather('df.feather')

# 读取
df = pd.read_feather('df.feather')
```

### 使用 parquet（压缩）

```python
# 保存（推荐，用于大数据）
df.to_parquet('df.parquet', compression='snappy')

# 读取
df = pd.read_parquet('df.parquet')
```

## 6. 调试大文件

### 先读取小样本

```python
# 先读100行看结构
df_sample = pd.read_csv('large_file.csv', nrows=100)
print(df_sample.columns)
print(df_sample.dtypes)
```

### 检查数据质量

```python
# 快速统计
df.describe()

# 检查缺失值
df.isnull().sum()

# 检查重复
df.duplicated().sum()
```

## 7. 使用 SQL 进行数据处理

```python
import sqlite3

# 创建内存数据库
conn = sqlite3.connect(':memory:')
df.to_sql('data', conn, index=False)

# 使用 SQL 查询
result = pd.read_sql('SELECT * FROM data WHERE col1 > 100', conn)
```

## 常见问题

1. **读取 Excel 超时**：使用 `nrows` 先读少量，或转 CSV
2. **内存不足**：删除不需要的列，使用 category 类型
3. **计算太慢**：使用向量化，避免循环
4. **保存太慢**：使用 parquet 格式（压缩快）
