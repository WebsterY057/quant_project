# IBKR AAPL 服务器运行手册

以下命令在 DuckDB 所在服务器执行。先把 `collectors/ingest_ibkr_l1_trade.py`、`aggregation/aggregate_ibkr_research.py` 和两份实际 YAML 上传到服务器项目目录。

## 环境变量

```bash
export RUSTFS_S3_ENDPOINT='YOUR_RUSTFS_ENDPOINT'
export RUSTFS_S3_ACCESS_KEY='YOUR_ACCESS_KEY'
export RUSTFS_S3_SECRET_KEY='YOUR_SECRET_KEY'
export RUSTFS_S3_REGION='us-east-1'
```

不要把真实凭据写进 YAML、脚本或 Git。

## 单日验证

```bash
python3 collectors/ingest_ibkr_l1_trade.py \
  --config config.ibkr_aapl.yaml \
  --tokens AAPL \
  --date-start 2026-07-07 \
  --date-end 2026-07-07 \
  --markets us \
  --max-workers 1 \
  --output-dir output/validation_20260707 \
  2>&1 | tee logs/validation_20260707.log
```

## 全量采集

```bash
python3 collectors/ingest_ibkr_l1_trade.py \
  --config config.ibkr_aapl.yaml \
  --tokens AAPL \
  --date-start 2026-07-07 \
  --date-end 2026-08-07 \
  --markets us \
  --max-workers 1 \
  --output-dir output/full_20260707_20260807 \
  2>&1 | tee logs/full_20260707_20260807.log
```

## 聚合与指标

```bash
python3 aggregation/aggregate_ibkr_research.py \
  --config config.ibkr_aapl_research.yaml \
  2>&1 | tee logs/aggregate_mt4_indicators.log
```

## 查看日志

```bash
tail -f logs/full_20260707_20260807.log
tail -f logs/aggregate_mt4_indicators.log
```

输出表为 `research.aapl_trade_bars_1m` 和 `research.aapl_trade_bars_5m`。时间口径为事件时间 UTC。
