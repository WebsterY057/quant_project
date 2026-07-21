# 外汇量化策略 - VWAP双均线交叉

## 策略说明

### 策略逻辑
- **VWAP双均线交叉**：快速VWAP(20) vs 慢速VWAP(60)
- **买入条件**：快线>慢线 + 趋势强度>0.0015 + 成交额过滤
- **卖出条件**：快线<慢线（死叉）

### 策略参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| VWAP_Fast_Period | 20 | VWAP快线周期 |
| VWAP_Slow_Period | 60 | VWAP慢线周期 |
| Buy_Confirm_Bars | 1 | 买入确认K线数 |
| Sell_Confirm_Bars | 4 | 卖出确认K线数 |
| Trend_Strength_Th | 0.0015 | 趋势强度阈值 |
| QV_Window | 60 | 成交额过滤窗口 |
| QV_Quantile | 0.10 | 成交额过滤分位 |

### 成本设置
- **点差(Spread)**：1点
- **手续费**：每0.01手 0.06（对应每手6美元）

### 货币对
已下载23天数据（2026-04-02 ~ 2026-04-25）：
- EURUSD, GBPUSD, USDJPY, USDCHF
- AUDUSD, NZDUSD, USDCAD
- EURGBP, EURJPY, GBPJPY

## 文件列表

### 数据
- `数据/` - 10个货币对的1分钟数据(CSV格式)

### 策略代码
- `VWAP_Strategy_v1.mq4` - MQL4 Expert Advisor

### 小红书书籍整理
- `book_series/` - 书籍主题台账和已生成的小红书成稿。
- `agents/` - 书籍知识拆解、社会语境映射、小红书成稿写作的角色文件。
- `skills/book-xiaohongshu-series/` - 维护书籍台账并生成下一篇成稿的 Codex skill。

## 使用方法

### 1. 安装EA到MT4
1. 打开MT4客户端
2. 文件 → 打开数据文件夹
3. 将 `VWAP_Strategy_v1.mq4` 复制到 `MQL4/Experts/` 目录
4. 重启MT4或在EA列表刷新

### 2. 编译
1. 在MT4导航器中找到 `VWAP_Strategy_v1`
2. 右键点击 → 编译
3. 确保无错误

### 3. 运行回测
1. 策略测试器 (Ctrl+R)
2. 选择EA: VWAP_Strategy_v1
3. 货币对: 选择对应货币对
4. 时间周期: 1分钟
5. 日期范围: 2026.04.02 - 2026.04.25
6. 开始回测

### 4. 参数优化
在策略测试器的"输入参数"标签页可以调整：
- VWAP周期
- 确认K线数
- 趋势阈值等

### 5. 小红书书籍台账流程
1. 在 `book_series/<book_slug>.md` 创建或更新书籍主题台账。
2. 从首个 `pending` 主题生成下一篇小红书成稿。
3. 成稿保存到 `book_series/posts/<book_slug>/<topic_id>_<YYYY-MM-DD>.md`。
4. 回写台账中的发布状态、发布日期和成稿路径。

Skill 细则见 `skills/book-xiaohongshu-series/SKILL.md`。

## 数据更新

如需获取最新数据，运行：
```bash
cd /Users/yy/.hermes/workspace/db/回测项目/外汇项目
./venv/bin/python fetch_forex_data.py
```

## 注意事项

1. **数据限制**：Yahoo Finance 每次最多获取8天1分钟数据
2. **点差**：默认1点，实际点差可能因时间段不同
3. **滑点**：建议设置3-5点
4. **风险提示**：外汇交易有风险，请先在模拟账户测试
