#!/usr/bin/env python3
"""
使用 Polygon.io API 获取外汇数据（免费tier有限制）
注册地址: https://polygon.io/
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


POLYGON_API_KEY = "YOUR_POLYGON_API_KEY"


INSTRUMENTS = [
    "C:EURUSD",
    "C:GBPUSD",
    "C:USDJPY",
    "C:USDCHF",
    "C:AUDUSD",
    "C:NZDUSD",
    "C:USDCAD",
    "C:EURGBP",
    "C:EURJPY",
    "C:GBPJPY",
]


def fetch_forex_polygon(ticker: str, from_date: datetime, to_date: datetime, output_dir: Path) -> pd.DataFrame:
    """从 Polygon.io 获取数据"""
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{from_date.strftime('%Y-%m-%d')}/{to_date.strftime('%Y-%m-%d')}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000,
        "apiKey": POLYGON_API_KEY,
    }

    print(f"  Fetching {ticker}...")
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"  Error: {response.status_code}")
        return pd.DataFrame()

    data = response.json()
    results = data.get("results", [])

    if not results:
        print(f"  No data")
        return pd.DataFrame()

    records = []
    for r in results:
        records.append({
            "Datetime": datetime.fromtimestamp(r["t"] / 1000),
            "Open": r["o"],
            "High": r["h"],
            "Low": r["l"],
            "Close": r["c"],
            "Volume": r["v"],
        })

    df = pd.DataFrame(records)
    pair_name = ticker.replace("C:", "")
    df.to_csv(output_dir / f"{pair_name}_M1_polygon.csv", index=False)
    print(f"  Got {len(df)} rows")
    return df


def main():
    output_dir = Path("/Users/yy/.hermes/workspace/db/回测项目/外汇项目/数据_polygon")
    output_dir.mkdir(parents=True, exist_ok=True)

    if POLYGON_API_KEY == "YOUR_POLYGON_API_KEY":
        print("=" * 60)
        print("Polygon.io API Key 未设置！")
        print("=" * 60)
        print("\n请按以下步骤操作:")
        print("1. 访问 https://polygon.io/ 注册免费账户")
        print("2. 获取 API Key")
        print("3. 编辑本文件，填入 POLYGON_API_KEY")
        print("4. 运行: python fetch_forex_polygon.py")
        print("\n注意: 免费账户有数据限制")
        return

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    print(f"Fetching forex data from Polygon.io...")
    print(f"Period: {start_date.date()} to {end_date.date()}")

    for ticker in INSTRUMENTS:
        fetch_forex_polygon(ticker, start_date, end_date, output_dir)

    print("\nDone!")


if __name__ == "__main__":
    main()