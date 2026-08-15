# Market Indicator Pipeline

当前策略版本：`v1.2.4`。策略口径、每笔固定 10 USD 的资金假设和因果性说明见 [docs/STRATEGY_V1.md](docs/STRATEGY_V1.md)。

从原始行情采集、历史回补、K 线聚合、MT4 指标计算到四板块可视化的可复现流水线。

## 数据板块

| 板块 | 标的 | 来源 | 历史范围 | 存储 |
|---|---|---|---|---|
| 美股 | AAPL | IBKR / RustFS | 2026-08-01—2026-08-10 | DuckDB |
| 代币化美股 | AAPLUSDT | Binance TradFi 永续历史 K 线 | 2026-08-01—2026-08-10 | SQLite |
| 加密货币 | BTC-USDT | OKX 历史 K 线 | 2026-08-01—2026-08-10 | SQLite |
| 外汇 | XAUUSD | Dukascopy ticks | 2026-07-13—2026-08-13 | SQLite |

图表统一展示 Smoothed Heiken Ashi（SMMA6/LWMA2）、ZigZag（D30/Dev3/B3）和 Parabolic SAR（0.016/0.2）。

## 目录

- `collectors/`：IBKR/RustFS 采集、Binance/OKX 历史回补与可选实时采集、Dukascopy 下载。
- `aggregation/`：IBKR 和 XAUUSD 的 1m/5m 聚合及指标落库。
- `configs/`：不含密钥的配置模板。
- `web/`：Flask + ECharts 四板块页面，默认端口 5011。
- `sql/`：DuckDB 表结构和样本检查。
- `docs/`：服务器执行手册。
- `data/`：运行时数据库目录，不提交 Git。

## 初始化

```bash
cd market_indicator_pipeline
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp web/config.example.yaml web/config.yaml
```

将示例配置复制为实际配置后再填写路径。密钥只通过环境变量提供，参考 `.env.example`，不要提交真实 `.env`。

## Binance 代币化美股永续历史数据

```bash
cp configs/config.binance_tokenized.example.yaml config.binance_tokenized.yaml
.venv/bin/python collectors/backfill_binance_history.py --config config.binance_tokenized.yaml
```

时间使用 Binance K 线开盘时间（event time，UTC）；`volume` 是 AAPL 数量，`trade_count` 是该分钟真实成交笔数。

## OKX 加密货币历史数据

```bash
cp configs/config.okx_btc_history.example.yaml config.okx_btc_history.yaml

.venv/bin/python collectors/backfill_okx_history.py --config config.okx_btc_history.yaml
```

时间使用 OKX K 线 `ts`（event time，UTC）。历史 K 线没有逐笔成交数量，`trade_count=0`；不能把它当作完整逐笔数据回测。

## Dukascopy XAUUSD

```bash
cp configs/config.dukascopy_xauusd.example.yaml config.dukascopy_xauusd.yaml
.venv/bin/python collectors/dukascopy_xauusd_downloader.py --config config.dukascopy_xauusd.yaml
.venv/bin/python aggregation/aggregate_dukascopy_bars.py --config config.dukascopy_xauusd.yaml
```

周末、每日维护窗口和节假日休市不应填充为虚假行情。

## IBKR / RustFS / DuckDB

```bash
cp configs/config.ibkr_aapl.example.yaml config.ibkr_aapl.yaml
cp configs/config.ibkr_aapl_research.example.yaml config.ibkr_aapl_research.yaml

.venv/bin/python collectors/ingest_ibkr_l1_trade.py --config config.ibkr_aapl.yaml
.venv/bin/python aggregation/aggregate_ibkr_research.py --config config.ibkr_aapl_research.yaml
```

详细的服务器命令见 `docs/IBKR_AAPL_RUNBOOK.md`。信号和 K 线使用事件时间；SSH 密码和 RustFS 凭据不写入代码。

## 启动可视化

```bash
cd web
export AAPL_VIS_REMOTE_PASSWORD='SSH password'
./start.sh
```

打开 `http://127.0.0.1:5011/`。若不启用远程美股板块，可设置 `AAPL_VIS_SKIP_REMOTE_AUTH=1`，其他本地板块仍可使用。

## 数据文件策略

仓库不包含大型运行时数据库：XAUUSD 原库约 2.2 GB，美股 DuckDB 位于服务器。请通过上述采集/回补脚本复现。`data/`、日志、PID、虚拟环境及密钥均已加入 `.gitignore`。
