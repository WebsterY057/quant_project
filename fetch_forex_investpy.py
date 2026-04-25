#!/usr/bin/env python3
"""
使用 investpy 获取外汇数据
"""

import investpy
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path


FOREX_PAIRS = [
    ("EURUSD", "eur", "usd"),
    ("GBPUSD", "gbp", "usd"),
    ("USDJPY", "usd", "jpy"),
    ("USDCHF", "usd", "chf"),
    ("AUDUSD", "aud", "usd"),
    ("NZDUSD", "nzd", "usd"),
    ("USDCAD", "usd", "cad"),
    ("EURGBP", "eur", "gbp"),
    ("EURJPY", "eur", "jpy"),
    ("GBPJPY", "gbp", "jpy"),
]


def fetch_forex_investpy(pair_name: str, from_date: str, to_date: str, output_dir: Path) -> pd.DataFrame:
    print(f"Fetching {pair_name}...")
    try:
        symbol = f"{pair_name[:3]}/{pair_name[3:]}"
        df = investpy.get_currency_cross_historical_data(
            currency_cross=pair_name,
            from_date=from_date,
            to_date=to_date,
        )
        if df.empty:
            print(f"  No data for {pair_name}")
            return df

        df.to_csv(output_dir / f"{pair_name.replace('/', '')}_investpy.csv")
        print(f"  Got {len(df)} rows")
        return df
    except Exception as e:
        print(f"  Error fetching {pair_name}: {e}")
        return pd.DataFrame()


def main():
    output_dir = Path("/Users/yy/.hermes/workspace/db/回测项目/外汇项目/数据_investpy")
    output_dir.mkdir(parents=True, exist_ok=True)

    from_date = "01/04/2026"
    to_date = "25/04/2026"

    print(f"Fetching forex data from {from_date} to {to_date}")
    print(f"Output directory: {output_dir}")
    print("-" * 60)

    for base, quote1, quote2 in FOREX_PAIRS:
        pair_name = f"{base}{quote2}"
        fetch_forex_investpy(pair_name, from_date, to_date, output_dir)

    print("-" * 60)
    print("Done!")


if __name__ == "__main__":
    main()