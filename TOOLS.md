# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## 🔐 加密货币数据分析

### 已安装 Skills
- `crypto-analysis` — 加密货币K线、订单簿获取与技术指标计算

### 环境
- Python 3.9 + pandas + numpy + matplotlib + scipy + jupyter
- 访问交易所 API 可能需要代理

### 常用工具
```bash
# 启动 Jupyter
jupyter notebook

# 获取K线数据 (在 python/jupiter 中)
from crypto_analysis.scripts.crypto_data import get_klines, get_ticker, get_orderbook
df = get_klines("BTCUSDT", "1h", 100)
```

### 注意事项
- 中国大陆访问 Binance/OKX 等可能需要代理
- 量化交易有风险，回测优先
