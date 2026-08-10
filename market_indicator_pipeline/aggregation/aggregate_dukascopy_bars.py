#!/usr/bin/env python3
"""Aggregate Dukascopy ticks into 1-minute and 5-minute quote bars."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise SystemExit("Missing dependency: pip install pyyaml") from exc


BAR_TABLES = {
    "1m": ("bars_1m", 60_000),
    "5m": ("bars_5m", 300_000),
}


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ValueError(f"Config is not a mapping: {path}")
    return cfg


def resolve_sqlite_path(config_path: Path, cfg: dict[str, Any], override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    sqlite_path = Path(cfg["output"]["sqlite_path"]).expanduser()
    if sqlite_path.is_absolute():
        return sqlite_path
    candidates = [
        config_path.parent / sqlite_path,
        config_path.parent.parent / sqlite_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def create_bar_table(conn: sqlite3.Connection, table_name: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,
            window_start_ms_utc INTEGER NOT NULL,
            window_start_utc TEXT NOT NULL,
            window_end_ms_utc INTEGER NOT NULL,
            window_end_utc TEXT NOT NULL,
            bid_open REAL NOT NULL,
            bid_high REAL NOT NULL,
            bid_low REAL NOT NULL,
            bid_close REAL NOT NULL,
            ask_open REAL NOT NULL,
            ask_high REAL NOT NULL,
            ask_low REAL NOT NULL,
            ask_close REAL NOT NULL,
            mid_open REAL NOT NULL,
            mid_high REAL NOT NULL,
            mid_low REAL NOT NULL,
            mid_close REAL NOT NULL,
            spread_open REAL NOT NULL,
            spread_high REAL NOT NULL,
            spread_low REAL NOT NULL,
            spread_close REAL NOT NULL,
            spread_avg REAL NOT NULL,
            bid_volume_sum REAL NOT NULL,
            ask_volume_sum REAL NOT NULL,
            tick_count INTEGER NOT NULL,
            first_tick_ms_utc INTEGER NOT NULL,
            last_tick_ms_utc INTEGER NOT NULL,
            generated_at_utc TEXT NOT NULL,
            PRIMARY KEY (symbol, window_start_ms_utc)
        )
        """
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_symbol_time "
        f"ON {table_name}(symbol, window_start_ms_utc)"
    )


def refresh_bar_table(conn: sqlite3.Connection, table_name: str, interval: str, bucket_ms: int) -> int:
    create_bar_table(conn, table_name)
    conn.execute(f"DELETE FROM {table_name}")
    insert_sql = f"""
        INSERT INTO {table_name} (
            symbol, interval, window_start_ms_utc, window_start_utc,
            window_end_ms_utc, window_end_utc,
            bid_open, bid_high, bid_low, bid_close,
            ask_open, ask_high, ask_low, ask_close,
            mid_open, mid_high, mid_low, mid_close,
            spread_open, spread_high, spread_low, spread_close, spread_avg,
            bid_volume_sum, ask_volume_sum, tick_count,
            first_tick_ms_utc, last_tick_ms_utc, generated_at_utc
        )
        VALUES (
            ?, ?, ?,
            strftime('%Y-%m-%dT%H:%M:%fZ', ? / 1000.0, 'unixepoch'),
            ?,
            strftime('%Y-%m-%dT%H:%M:%fZ', ? / 1000.0, 'unixepoch'),
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        )
    """

    def make_row(bar: dict[str, Any]) -> tuple[Any, ...]:
        window_end = int(bar["window_start_ms_utc"]) + bucket_ms
        tick_count = int(bar["tick_count"])
        spread_avg = float(bar["spread_sum"]) / tick_count
        return (
            bar["symbol"],
            interval,
            bar["window_start_ms_utc"],
            bar["window_start_ms_utc"],
            window_end,
            window_end,
            bar["bid_open"],
            bar["bid_high"],
            bar["bid_low"],
            bar["bid_close"],
            bar["ask_open"],
            bar["ask_high"],
            bar["ask_low"],
            bar["ask_close"],
            bar["mid_open"],
            bar["mid_high"],
            bar["mid_low"],
            bar["mid_close"],
            bar["spread_open"],
            bar["spread_high"],
            bar["spread_low"],
            bar["spread_close"],
            spread_avg,
            bar["bid_volume_sum"],
            bar["ask_volume_sum"],
            tick_count,
            bar["first_tick_ms_utc"],
            bar["last_tick_ms_utc"],
        )

    def new_bar(
        symbol: str,
        timestamp_ms_utc: int,
        bid: float,
        ask: float,
        bid_volume: float,
        ask_volume: float,
    ) -> dict[str, Any]:
        window_start = (timestamp_ms_utc // bucket_ms) * bucket_ms
        mid = (bid + ask) / 2.0
        spread = ask - bid
        return {
            "symbol": symbol,
            "window_start_ms_utc": window_start,
            "bid_open": bid,
            "bid_high": bid,
            "bid_low": bid,
            "bid_close": bid,
            "ask_open": ask,
            "ask_high": ask,
            "ask_low": ask,
            "ask_close": ask,
            "mid_open": mid,
            "mid_high": mid,
            "mid_low": mid,
            "mid_close": mid,
            "spread_open": spread,
            "spread_high": spread,
            "spread_low": spread,
            "spread_close": spread,
            "spread_sum": spread,
            "bid_volume_sum": bid_volume,
            "ask_volume_sum": ask_volume,
            "tick_count": 1,
            "first_tick_ms_utc": timestamp_ms_utc,
            "last_tick_ms_utc": timestamp_ms_utc,
        }

    def update_bar(
        bar: dict[str, Any],
        timestamp_ms_utc: int,
        bid: float,
        ask: float,
        bid_volume: float,
        ask_volume: float,
    ) -> None:
        mid = (bid + ask) / 2.0
        spread = ask - bid
        bar["bid_high"] = max(bar["bid_high"], bid)
        bar["bid_low"] = min(bar["bid_low"], bid)
        bar["bid_close"] = bid
        bar["ask_high"] = max(bar["ask_high"], ask)
        bar["ask_low"] = min(bar["ask_low"], ask)
        bar["ask_close"] = ask
        bar["mid_high"] = max(bar["mid_high"], mid)
        bar["mid_low"] = min(bar["mid_low"], mid)
        bar["mid_close"] = mid
        bar["spread_high"] = max(bar["spread_high"], spread)
        bar["spread_low"] = min(bar["spread_low"], spread)
        bar["spread_close"] = spread
        bar["spread_sum"] += spread
        bar["bid_volume_sum"] += bid_volume
        bar["ask_volume_sum"] += ask_volume
        bar["tick_count"] += 1
        bar["last_tick_ms_utc"] = timestamp_ms_utc

    rows: list[tuple[Any, ...]] = []
    current: dict[str, Any] | None = None
    cursor = conn.execute(
        """
        SELECT symbol, timestamp_ms_utc, bid, ask, bid_volume, ask_volume
        FROM ticks
        ORDER BY symbol, timestamp_ms_utc
        """
    )
    for symbol, timestamp_ms_utc, bid, ask, bid_volume, ask_volume in cursor:
        timestamp_ms_utc = int(timestamp_ms_utc)
        window_start = (timestamp_ms_utc // bucket_ms) * bucket_ms
        if current is None or current["symbol"] != symbol or current["window_start_ms_utc"] != window_start:
            if current is not None:
                rows.append(make_row(current))
            current = new_bar(symbol, timestamp_ms_utc, bid, ask, bid_volume, ask_volume)
        else:
            update_bar(current, timestamp_ms_utc, bid, ask, bid_volume, ask_volume)
        if len(rows) >= 10_000:
            conn.executemany(insert_sql, rows)
            conn.commit()
            rows.clear()
    if current is not None:
        rows.append(make_row(current))
    if rows:
        conn.executemany(insert_sql, rows)
    conn.commit()
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--sqlite-path")
    parser.add_argument("--interval", choices=sorted(BAR_TABLES), action="append")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    cfg = load_config(config_path)
    db_path = resolve_sqlite_path(config_path, cfg, args.sqlite_path)
    intervals = args.interval or sorted(BAR_TABLES)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    try:
        for interval in intervals:
            table_name, bucket_ms = BAR_TABLES[interval]
            row_count = refresh_bar_table(conn, table_name, interval, bucket_ms)
            print(f"{table_name} rows={row_count}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
