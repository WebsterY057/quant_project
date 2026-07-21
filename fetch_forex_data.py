#!/usr/bin/env python3
"""
获取外汇主流货币对的1分钟数据
Yahoo Finance 每次最多获取8天的1分钟数据
"""

import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

# 主流货币对列表
FOREX_PAIRS = [
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "USDCHF=X",
    "AUDUSD=X",
    "NZDUSD=X",
    "USDCAD=X",
    "EURGBP=X",
    "EURJPY=X",
    "GBPJPY=X",
]

MAX_DAYS_PER_REQUEST = 7  # Yahoo限制8天，这里用7天保险


def fetch_forex_data_in_chunks(pair: str, start_date: datetime, end_date: datetime, output_dir: Path) -> pd.DataFrame:
    print(f"Fetching {pair}...")
    all_data = []
    current_start = start_date

    while current_start < end_date:
        current_end = min(current_start + timedelta(days=MAX_DAYS_PER_REQUEST), end_date)
        try:
            ticker = yf.Ticker(pair)
            df = ticker.history(
                start=current_start.strftime("%Y-%m-%d"),
                end=current_end.strftime("%Y-%m-%d"),
                interval="1m"
            )
            if not df.empty:
                all_data.append(df)
                print(f"  {current_start.date()} to {current_end.date()}: {len(df)} rows")
        except Exception as e:
            print(f"  Error: {e}")

        current_start = current_end

    if all_data:
        combined = pd.concat(all_data)
        combined.to_csv(output_dir / f"{pair.replace('=X', '')}_1min.csv")
        print(f"  Total: {len(combined)} rows saved")
        return combined
    else:
        print(f"  No data for {pair}")
        return pd.DataFrame()


def main():
    output_dir = Path("/Users/yy/.hermes/workspace/db/回测项目/外汇项目/数据")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 获取最近30天的数据
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    print(f"Fetching forex data from {start_date.date()} to {end_date.date()}")
    print(f"Output directory: {output_dir}")
    print("-" * 60)

    for pair in FOREX_PAIRS:
        fetch_forex_data_in_chunks(pair, start_date, end_date, output_dir)

    print("-" * 60)
    print("Done!")


if __name__ == "__main__":
    main()