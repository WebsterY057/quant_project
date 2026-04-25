#!/usr/bin/env python3
"""
使用 OANDA API 获取外汇分钟数据
需要注册 OANDA 账户获取 API Key

注册地址: https://www.oanda.com/
免费模拟账户: https://www.oanda.com/demo-account/

注册后获取 API Key，填入下方 OANDA_API_KEY
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


# ============== 请填入你的 OANDA API Key ==============
OANDA_API_KEY = "YOUR_OANDA_API_KEY_HERE"
OANDA_ACCOUNT_ID = "YOUR_ACCOUNT_ID_HERE"
# ====================================================

OANDA_BASE_URL = "https://api-fxpractice.oanda.com/v3"
OANDA_STREAM_URL = "https://stream-fxpractice.oanda.com/v3"

INSTRUMENTS = [
    "EUR_USD",
    "GBP_USD",
    "USD_JPY",
    "USD_CHF",
    "AUD_USD",
    "NZD_USD",
    "USD_CAD",
    "EUR_GBP",
    "EUR_JPY",
    "GBP_JPY",
]


def fetch_ohlc_from_oanda(instrument: str, granularity: str, from_time: str, to_time: str) -> pd.DataFrame:
    """从 OANDA API 获取 K线数据"""
    url = f"{OANDA_BASE_URL}/instruments/{instrument}/candles"
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}",
        "Content-Type": "application/json",
    }
    params = {
        "from": from_time,
        "to": to_time,
        "granularity": granularity,
        "price": "M",
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"  Error: {response.status_code} - {response.text}")
        return pd.DataFrame()

    data = response.json()
    candles = data.get("candles", [])

    if not candles:
        return pd.DataFrame()

    records = []
    for c in candles:
        mid = c.get("mid", {})
        records.append({
            "Datetime": c["time"],
            "Open": float(mid["o"]),
            "High": float(mid["h"]),
            "Low": float(mid["l"]),
            "Close": float(mid["c"]),
            "Volume": int(c.get("volume", 0)),
        })

    df = pd.DataFrame(records)
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    return df


def fetch_forex_data_oanda(days: int = 30):
    """获取外汇数据"""
    output_dir = Path("/Users/yy/.hermes/workspace/db/回测项目/外汇项目/数据_oanda")
    output_dir.mkdir(parents=True, exist_ok=True)

    if OANDA_API_KEY == "YOUR_OANDA_API_KEY_HERE":
        print("请先填写 OANDA_API_KEY！")
        print("注册地址: https://www.oanda.com/")
        return

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

    from_time = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    to_time = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Fetching forex data from OANDA...")
    print(f"Period: {from_time} to {to_time}")
    print(f"Output: {output_dir}")
    print("-" * 60)

    for instrument in INSTRUMENTS:
        pair_name = instrument.replace("_", "")
        print(f"Fetching {pair_name}...")

        df = fetch_ohlc_from_oanda(instrument, "M1", from_time, to_time)

        if not df.empty:
            output_file = output_dir / f"{pair_name}_M1_oanda.csv"
            df.to_csv(output_file, index=False)
            print(f"  Saved {len(df)} rows to {output_file}")
        else:
            print(f"  No data fetched")

    print("-" * 60)
    print("Done!")
    print(f"\n数据已保存到: {output_dir}")
    print(f"\n注意: OANDA 模拟账户有数据限制，请确保使用有效的 API Key")


def main():
    import sys

    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    else:
        days = 30

    if OANDA_API_KEY == "YOUR_OANDA_API_KEY_HERE":
        print("=" * 60)
        print("OANDA API Key 未设置！")
        print("=" * 60)
        print("\n请按以下步骤操作:")
        print("1. 访问 https://www.oanda.com/ 注册账户")
        print("2. 登录后获取 API Key: https://www.oanda.com/account/tpa/personal_token")
        print("3. 编辑本文件，填入 OANDA_API_KEY")
        print("4. 运行: python fetch_forex_oanda.py")
        print("=" * 60)
        return

    fetch_forex_data_oanda(days)


if __name__ == "__main__":
    main()