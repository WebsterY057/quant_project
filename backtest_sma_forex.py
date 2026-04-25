#!/usr/bin/env python3
"""
外汇VWAP策略 - 改用SMA（简单移动平均）
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

import numpy as np
import pandas as pd


@dataclass
class ForexConfig:
    vwap_sustain: int = 1
    sma_fast_window: int = 20
    sma_slow_window: int = 60
    buy_confirm_bars: int = 1
    sell_confirm_bars: int = 4
    trend_strength_threshold: float = 0.0015
    fee_per_lot: float = 6.0
    spread_points: float = 1.0


FOREX_CONFIG = ForexConfig()


def add_signals(
    bars: pd.DataFrame,
    sma_fast_window: int = 20,
    sma_slow_window: int = 60,
    buy_confirm_bars: int = 1,
    sell_confirm_bars: int = 4,
    trend_threshold: float = 0.0015,
) -> pd.DataFrame:
    df = bars.copy()

    df["sma_fast"] = df["close"].rolling(sma_fast_window, min_periods=sma_fast_window).mean()
    df["sma_slow"] = df["close"].rolling(sma_slow_window, min_periods=sma_slow_window).mean()

    above = (df["sma_fast"] > df["sma_slow"]).astype(int)
    below = (df["sma_fast"] < df["sma_slow"]).astype(int)

    df["sma_buy"] = (above.rolling(buy_confirm_bars, min_periods=buy_confirm_bars).sum() >= buy_confirm_bars).astype(int)
    df["sma_sell"] = (below.rolling(sell_confirm_bars, min_periods=sell_confirm_bars).sum() >= sell_confirm_bars).astype(int)

    if "sma_fast" in df.columns and "sma_slow" in df.columns:
        trend_spread = (df["sma_fast"] / df["sma_slow"] - 1.0).replace([np.inf, -np.inf], np.nan)
    else:
        trend_spread = 0

    df["trend_pass"] = (trend_spread >= trend_threshold).fillna(False).astype(int)

    df["buy_signal"] = (df["sma_buy"] == 1) & (df["trend_pass"] == 1)
    df["sell_signal"] = (df["sma_sell"] == 1)

    return df


def run_backtest(
    df: pd.DataFrame,
    fee_per_lot: float = 6.0,
    spread_points: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = df.copy().reset_index(drop=True)

    if len(data) < 60:
        return pd.DataFrame(), pd.DataFrame()

    spread_cost = spread_points * data["close"].iloc[0] * 0.0001
    fee = fee_per_lot * data["close"].iloc[0] * 0.01

    position = 0
    entry_price = np.nan
    entry_time = None
    sell_streak = 0
    positions = []
    trades = []
    equity = np.zeros(len(data))
    capital = 1.0
    units = 0.0
    prev_equity = 1.0
    net_ret = np.zeros(len(data))

    for i in range(len(data)):
        buy = bool(data.at[i, "buy_signal"])
        sell = bool(data.at[i, "sell_signal"])
        px = float(data.at[i, "close"])
        ts = data.at[i, "datetime"]

        if sell:
            sell_streak += 1
        else:
            sell_streak = 0
        signal_confirmed = sell_streak >= max(1, data.get("sell_confirm_bars", 4))

        if position == 1 and signal_confirmed:
            trade_ret = (px / entry_price - 1.0) * 100.0 - spread_cost / entry_price * 100.0 - fee / entry_price * 100.0
            trades.append({
                "entry_time": entry_time,
                "exit_time": ts,
                "entry_price": entry_price,
                "exit_price": px,
                "return_pct": trade_ret,
                "exit_reason": "signal_sell",
            })
            position = 0
            entry_price = np.nan
            entry_time = None
            sell_streak = 0
            capital = units * px
            units = 0.0
        elif position == 0 and buy and not sell:
            position = 1
            entry_price = px
            entry_time = ts
            units = capital / entry_price

        positions.append(position)
        cur_equity = units * px if position == 1 else capital
        equity[i] = cur_equity
        net_ret[i] = cur_equity / prev_equity - 1.0 if i > 0 and prev_equity > 0 else 0.0
        prev_equity = cur_equity if cur_equity > 0 else prev_equity

    if position == 1:
        px = float(data.at[len(data) - 1, "close"])
        ts = data.at[len(data) - 1, "Datetime"]
        trade_ret = (px / entry_price - 1.0) * 100.0 - spread_cost / entry_price * 100.0 - fee / entry_price * 100.0
        trades.append({
            "entry_time": entry_time,
            "exit_time": ts,
            "entry_price": entry_price,
            "exit_price": px,
            "return_pct": trade_ret,
            "exit_reason": "final_close",
        })
        capital = units * px
        units = 0.0
        equity[-1] = capital

    data["position"] = positions
    data["strategy_ret"] = net_ret
    data["equity"] = equity
    trades_df = pd.DataFrame(trades)
    return data, trades_df


def summarize(results: pd.DataFrame, trades: pd.DataFrame) -> dict:
    if results.empty:
        return {
            "total_return_pct": np.nan,
            "max_drawdown_pct": np.nan,
            "win_rate_pct": np.nan,
            "num_trades": 0,
            "avg_trade_return_pct": np.nan,
        }

    total_return = (results["equity"].iloc[-1] - 1.0) * 100.0
    roll_max = results["equity"].cummax()
    drawdown = results["equity"] / roll_max - 1.0
    max_dd = drawdown.min() * 100.0
    num_trades = len(trades)
    win_rate = (trades["return_pct"] > 0).mean() * 100.0 if num_trades > 0 else np.nan
    avg_trade = trades["return_pct"].mean() if num_trades > 0 else np.nan

    return {
        "total_return_pct": total_return,
        "max_drawdown_pct": max_dd,
        "win_rate_pct": win_rate,
        "num_trades": num_trades,
        "avg_trade_return_pct": avg_trade,
    }


def process_symbol(symbol: str, csv_path: Path, config: ForexConfig) -> dict:
    df = pd.read_csv(csv_path)

    if "close" not in df.columns and "Close" not in df.columns:
        return {"symbol": symbol, "error": "missing columns"}

    df.columns = [c.lower() for c in df.columns]
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")

    sig = add_signals(
        df,
        sma_fast_window=config.sma_fast_window,
        sma_slow_window=config.sma_slow_window,
        buy_confirm_bars=config.buy_confirm_bars,
        sell_confirm_bars=config.sell_confirm_bars,
        trend_threshold=config.trend_strength_threshold,
    )

    results, trades = run_backtest(
        sig,
        fee_per_lot=config.fee_per_lot,
        spread_points=config.spread_points,
    )

    summary = summarize(results, trades)
    summary["symbol"] = symbol
    return summary


def main():
    config = ForexConfig()
    data_dir = Path("/Users/yy/.hermes/workspace/db/回测项目/外汇项目/数据")
    output_dir = Path("/Users/yy/.hermes/workspace/db/回测项目/外汇项目/报告_SMA")
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(data_dir.glob("*_1min.csv"))

    results = []
    num_workers = min(multiprocessing.cpu_count(), 4)

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_symbol, f.stem.replace("_1min", ""), f, config): f for f in csv_files}
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                print(f"Completed: {res.get('symbol', 'unknown')}")

    df_results = pd.DataFrame(results)

    df_results.to_csv(output_dir / "回测汇总.csv", index=False)

    with open(output_dir / "回测报告.md", "w", encoding="utf-8") as f:
        f.write("# 外汇SMA策略回测报告\n\n")
        f.write(f"- SMA快线周期: {config.sma_fast_window}\n")
        f.write(f"- SMA慢线周期: {config.sma_slow_window}\n")
        f.write(f"- 买入确认K: {config.buy_confirm_bars}\n")
        f.write(f"- 卖出确认K: {config.sell_confirm_bars}\n")
        f.write(f"- 趋势阈值: {config.trend_strength_threshold}\n")
        f.write(f"- 点差: {config.spread_points}点\n")
        f.write(f"- 手续费: ${config.fee_per_lot}/手\n\n")

        f.write("## 汇总\n\n")
        df_valid = df_results.dropna(subset=["total_return_pct"])
        if not df_valid.empty:
            avg_ret = df_valid["total_return_pct"].mean()
            avg_dd = df_valid["max_drawdown_pct"].mean()
            avg_wr = df_valid["win_rate_pct"].mean()
            pos_count = (df_valid["total_return_pct"] > 0).sum()
            f.write(f"- 平均收益率: {avg_ret:.2f}%\n")
            f.write(f"- 平均最大回撤: {avg_dd:.2f}%\n")
            f.write(f"- 平均胜率: {avg_wr:.2f}%\n")
            f.write(f"- 正收益货币对数: {pos_count}/{len(df_valid)}\n\n")

        f.write("## 逐货币对明细\n\n")
        f.write("| 货币对 | 收益率(%) | 最大回撤(%) | 胜率(%) | 交易次数 | 平均收益(%) |\n")
        f.write("|---|---|---|---|---|---|\n")
        for _, row in df_valid.sort_values("total_return_pct", ascending=False).iterrows():
            f.write(f"| {row['symbol']} | {row['total_return_pct']:.2f} | {row['max_drawdown_pct']:.2f} | {row['win_rate_pct']:.2f} | {int(row['num_trades'])} | {row['avg_trade_return_pct']:.4f} |\n")

    print(f"\nDone! Results saved to {output_dir}")


if __name__ == "__main__":
    main()