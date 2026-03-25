# MEMORY.md - 长期记忆

## 用户信息
- **称呼：** 未提供具体姓名
- **语言：** 中文
- **时区：** Asia/Shanghai (GMT+8)

## 用户背景
- 在一家**区块链量化交易公司**从事**加密货币数据分析**工作
- 公司主要做**套利策略**：CEX 吃单 → DEX 执行 → 捆绑平台上链
- 策略核心：CEX 买一卖一价格作为触发信号，在 DEX 上进行交易

## 当前项目：套利 Alpha 归因分析

### 目标
找出**实际利润高于理论利润**的 Alpha 来源

### Alpha 计算方式
```
Alpha = 实际利润 - 理论利润 - BNB 仓位影响
```
- 实际利润 = `Single_PL`（已扣除滑点）
- 理论利润 = `Profit_virtual_fee`（第一套计算：稳定币交易量 - token交易量 × 交易所价格）
- BNB 影响 = BNB 价格变化 × BNB 数量变化

### 核心问题
"为什么实际成交比理论预期更好？"

### 可能的 Alpha 来源
- ⏱ 时间差优势
- 🔀 捆绑 Alpha（Gas 优化、排序优势）
- 🏛 MEV 捕获
- 📊 盘口结构 Alpha

### 数据情况
- 数据量：10000+ 条记录
- 策略：24小时全天候运行
- 数据字段已整理（见下方）

### 数据字段（关键）
| 字段 | 说明 |
|------|------|
| `Time` | 时间 |
| `Block` | 区块号 |
| `Single_PL` | 单笔盈亏 |
| `Stable_totalPL` | 今日稳定币盈亏 |
| `Totalpl` | 今日交易对盈亏 |
| `Profit_virtual` | 带手续费理论利润 |
| `Profit_virtual_fee` | 理论利润 |
| `Gasfee` | Gas 费（U） |
| `Bundle` | 捆绑费 |
| `Bundle_rate` | 捆绑比例 |
| `Price_diff` | 价差 |
| `Maxpair_stable_reserve` | 稳定币库存 |
| `Maxpair_token_reserve` | token 库存 |
| `Bnb_singlePL` | BNB 单笔自增长盈亏 |
| `Bnb_amount` | BNB 剩余持仓 |

## 已安装技能
- `crypto-analysis` — 加密货币 K 线、订单簿获取与技术指标计算

## 技术环境
- Python 3.9 + pandas + numpy + matplotlib + scipy + jupyter
- Jupyter 工作目录已配置

## 待办/跟进
- [ ] 接收用户数据文件（10000+ 条 CSV/Excel）
- [ ] 进行 Alpha 归因分析
- [ ] 找出利润高于理论预期的真实来源
- [ ] 验证 Alpha 稳健性
- [ ] 探讨 Alpha 实际利用方案
