#!/usr/bin/env python3
"""
使用 frankfurter.app API 获取外汇数据（免费，无需密钥）
"""

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path


def fetch_forex_frankfurter(base: str, quote: str, start: str, end: str, output_dir: Path) -> pd.DataFrame:
    print(f"Fetching {base}/{quote}...")

    try:
        url = f"https://api.frankfurter.app/{start}..{end}"
        params = {"from": base, "to": quote}

        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if "rates" not in data:
            print(f"  API failed: {data}")
            return pd.DataFrame()

        rates = data["rates"]
        records = []
        for date_str, rate in rates.items():
            records.append({
                "Datetime": date_str,
                "Close": rate,
                "Open": rate,
                "High": rate,
                "Low": rate,
                "Volume": 0,
            })

        if not records:
            print(f"  No data for {base}/{quote}")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df = df.sort_values("Datetime")

        pair_name = f"{base}{quote}"
        df.to_csv(output_dir / f"{pair_name}_frankfurter.csv", index=False)
        print(f"  Got {len(df)} rows from {df['Datetime'].min()} to {df['Datetime'].max()}")
        return df

    except Exception as e:
        print(f"  Error fetching {base}/{quote}: {e}")
        return pd.DataFrame()


def main():
    output_dir = Path("/Users/yy/.hermes/workspace/db/回测项目/外汇项目/数据_frankfurter")
    output_dir.mkdir(parents=True, exist_ok=True)

    start = "2026-04-01"
    end = "2026-04-24"

    pairs = [
        ("EUR", "USD"),
        ("GBP", "USD"),
        ("USD", "JPY"),
        ("USD", "CHF"),
        ("AUD", "USD"),
        ("NZD", "USD"),
        ("USD", "CAD"),
    ]

    print(f"Fetching forex data from {start} to {end}")
    print(f"Output directory: {output_dir}")
    print("-" * 60)

    for base, quote in pairs:
        fetch_forex_frankfurter(base, quote, start, end, output_dir)

    print("-" * 60)
    print("Done!")


if __name__ == "__main__":
    main()