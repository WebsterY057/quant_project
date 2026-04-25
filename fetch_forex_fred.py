#!/usr/bin/env python3
"""
使用 pandas_datareader 从 FRED 获取外汇数据
"""

import pandas_datareader.data as web
from datetime import datetime
import pandas as pd
from pathlib import Path


# FRED 外汇符号
# DEXUSEU = US/Euro, DEXJPUS = Japan/US, etc.
FOREX_SYMBOLS = {
    "EURUSD": "DEXUSEU",
    "GBPUSD": "DEXUKUS",
    "USDJPY": "DEXJPUS",
    "USDCHF": "DEXSZUS",
    "AUDUSD": "DEXAUSUS",
    "NZDUSD": "DEXNZUS",
    "USDCAD": "DEXCAUS",
}


def fetch_forex_fred(symbol_name: str, fred_symbol: str, start: datetime, end: datetime, output_dir: Path) -> pd.DataFrame:
    print(f"Fetching {symbol_name} ({fred_symbol})...")
    try:
        df = web.DataReader(fred_symbol, 'fred', start, end)
        if df.empty:
            print(f"  No data for {fred_symbol}")
            return df

        df.columns = ["Close"]
        df["Open"] = df["Close"]
        df["High"] = df["Close"]
        df["Low"] = df["Close"]
        df["Volume"] = 0
        df.index = pd.to_datetime(df.index)
        df = df.reset_index()
        df.columns = ["Datetime", "Close", "Open", "High", "Low", "Volume"]

        df.to_csv(output_dir / f"{symbol_name}_fred.csv", index=False)
        print(f"  Got {len(df)} rows from {df['Datetime'].min()} to {df['Datetime'].max()}")
        return df
    except Exception as e:
        print(f"  Error fetching {fred_symbol}: {e}")
        return pd.DataFrame()


def main():
    output_dir = Path("/Users/yy/.hermes/workspace/db/回测项目/外汇项目/数据_fred")
    output_dir.mkdir(parents=True, exist_ok=True)

    start = datetime(2026, 4, 1)
    end = datetime(2026, 4, 25)

    print(f"Fetching forex data from {start.date()} to {end.date()}")
    print(f"Output directory: {output_dir}")
    print("-" * 60)

    for symbol_name, fred_symbol in FOREX_SYMBOLS.items():
        fetch_forex_fred(symbol_name, fred_symbol, start, end, output_dir)

    print("-" * 60)
    print("Done!")


if __name__ == "__main__":
    main()