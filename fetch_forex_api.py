#!/usr/bin/env python3
"""
使用 exchangerate.host API 获取外汇数据
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


def fetch_forex_exchangerate(pair: str, start: datetime, end: datetime, output_dir: Path) -> pd.DataFrame:
    print(f"Fetching {pair}...")

    try:
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        url = f"https://api.exchangerate.host/timeseries"
        params = {
            "base": pair[:3],
            "start_date": start_str,
            "end_date": end_str,
        }

        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if not data or data.get("success") != True or "rates" not in data:
            print(f"  API failed for {pair}: {data}")
            return pd.DataFrame()

        rates = data["rates"]
        records = []
        for date_str, rate_dict in rates.items():
            quote_currency = pair[3:]
            if quote_currency in rate_dict:
                records.append({
                    "Datetime": date_str,
                    "Close": rate_dict[quote_currency],
                    "Open": rate_dict[quote_currency],
                    "High": rate_dict[quote_currency],
                    "Low": rate_dict[quote_currency],
                    "Volume": 0,
                })

        if not records:
            print(f"  No rate data for {pair}")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df = df.sort_values("Datetime")

        df.to_csv(output_dir / f"{pair}_exchange.csv", index=False)
        print(f"  Got {len(df)} rows from {df['Datetime'].min()} to {df['Datetime'].max()}")
        return df

    except Exception as e:
        print(f"  Error fetching {pair}: {e}")
        return pd.DataFrame()


def main():
    output_dir = Path("/Users/yy/.hermes/workspace/db/回测项目/外汇项目/数据_exchangerate")
    output_dir.mkdir(parents=True, exist_ok=True)

    start = datetime(2026, 4, 1)
    end = datetime(2026, 4, 25)

    pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]

    print(f"Fetching forex data from {start.date()} to {end.date()}")
    print(f"Output directory: {output_dir}")
    print("-" * 60)

    for pair in pairs:
        fetch_forex_exchangerate(pair, start, end, output_dir)

    print("-" * 60)
    print("Done!")


if __name__ == "__main__":
    main()