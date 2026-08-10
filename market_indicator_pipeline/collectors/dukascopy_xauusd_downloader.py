#!/usr/bin/env python3
"""
Download Dukascopy XAUUSD tick files into SQLite.

Data source:
  https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{YYYY}/{MM_ZERO_BASED}/{DD}/{HH}h_ticks.bi5

The .bi5 payload is LZMA-compressed binary ticks. Each decoded record is:
  time_ms_from_hour, ask_price_int, bid_price_int, ask_volume, bid_volume
encoded as big-endian >IIIff.
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.client
import lzma
import sqlite3
import ssl
import struct
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise SystemExit("Missing dependency: pip install pyyaml") from exc


TICK_RECORD = struct.Struct(">IIIff")


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ValueError(f"Config is not a mapping: {path}")
    return cfg


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def iter_hours(start_date: dt.date, end_date_exclusive: dt.date):
    current = dt.datetime.combine(start_date, dt.time(), tzinfo=dt.timezone.utc)
    end = dt.datetime.combine(end_date_exclusive, dt.time(), tzinfo=dt.timezone.utc)
    while current < end:
        yield current
        current += dt.timedelta(hours=1)


def build_tick_url(base_url: str, symbol: str, hour: dt.datetime) -> str:
    month_zero_based = hour.month - 1
    return (
        f"{base_url.rstrip('/')}/{symbol}/"
        f"{hour.year:04d}/{month_zero_based:02d}/{hour.day:02d}/"
        f"{hour.hour:02d}h_ticks.bi5"
    )


def build_ssl_context(verify_tls: bool) -> ssl.SSLContext:
    if not verify_tls:
        return ssl._create_unverified_context()
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch_bytes(
    url: str,
    timeout: int,
    retries: int,
    sleep_seconds: int,
    ssl_context: ssl.SSLContext,
) -> bytes | None:
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
                if resp.status == 404:
                    return None
                payload = resp.read()
                return payload or None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if attempt >= retries:
                raise
        except urllib.error.URLError:
            if attempt >= retries:
                raise
        except (http.client.RemoteDisconnected, ConnectionResetError, TimeoutError):
            if attempt >= retries:
                raise
        time.sleep(sleep_seconds)
    return None


def decode_ticks(payload: bytes, hour: dt.datetime, price_scale: float):
    raw = lzma.decompress(payload)
    if len(raw) % TICK_RECORD.size != 0:
        raise ValueError(f"Decoded byte length is not a multiple of {TICK_RECORD.size}: {len(raw)}")

    for offset in range(0, len(raw), TICK_RECORD.size):
        ms_from_hour, ask_i, bid_i, ask_vol, bid_vol = TICK_RECORD.unpack_from(raw, offset)
        ts = hour + dt.timedelta(milliseconds=ms_from_hour)
        ask = ask_i / price_scale
        bid = bid_i / price_scale
        yield ts, bid, ask, bid_vol, ask_vol


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ticks (
            symbol TEXT NOT NULL,
            timestamp_ms_utc INTEGER NOT NULL,
            timestamp_utc TEXT NOT NULL,
            bid REAL NOT NULL,
            ask REAL NOT NULL,
            bid_volume REAL NOT NULL,
            ask_volume REAL NOT NULL,
            source_hour_utc TEXT NOT NULL,
            source_url TEXT NOT NULL,
            PRIMARY KEY (symbol, timestamp_ms_utc, bid, ask, bid_volume, ask_volume)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS download_hours (
            symbol TEXT NOT NULL,
            source_hour_utc TEXT NOT NULL,
            source_url TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_bytes INTEGER,
            tick_count INTEGER,
            downloaded_at_utc TEXT NOT NULL,
            error TEXT,
            PRIMARY KEY (symbol, source_hour_utc)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON ticks(symbol, timestamp_ms_utc)")
    conn.commit()
    return conn


def timestamp_ms(ts: dt.datetime) -> int:
    return int(ts.timestamp() * 1000)


def flush_tick_batch(conn: sqlite3.Connection, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    conn.executemany(
        """
        INSERT OR IGNORE INTO ticks (
            symbol, timestamp_ms_utc, timestamp_utc, bid, ask, bid_volume, ask_volume,
            source_hour_utc, source_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    rows.clear()


def already_downloaded(conn: sqlite3.Connection, symbol: str, source_hour: str) -> bool:
    row = conn.execute(
        "SELECT status FROM download_hours WHERE symbol = ? AND source_hour_utc = ?",
        (symbol, source_hour),
    ).fetchone()
    return bool(row and row[0] in {"ok", "missing"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="outputs/dukascopy_xauusd_config.yaml")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    symbol = str(cfg["symbol"]).replace("/", "").upper()
    start_date = parse_date(str(cfg["start_date_utc"]))
    end_date = parse_date(str(cfg["end_date_utc_exclusive"]))

    download_cfg = cfg["download"]
    decode_cfg = cfg["decode"]
    output_cfg = cfg["output"]

    output_dir = Path(output_cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw_bi5"
    sqlite_path = Path(output_cfg["sqlite_path"])
    keep_raw_bi5 = bool(output_cfg.get("keep_raw_bi5", True))
    batch_insert_rows = int(output_cfg.get("batch_insert_rows", 50000))

    price_scale = float(decode_cfg["price_scale"])
    ssl_context = build_ssl_context(bool(download_cfg.get("verify_tls", True)))
    conn = init_db(sqlite_path)
    tick_batch: list[tuple[Any, ...]] = []

    downloaded_hours = 0
    missing_hours = 0
    decoded_ticks = 0
    sample_prices: list[float] = []

    try:
        for hour in iter_hours(start_date, end_date):
            source_hour = hour.isoformat().replace("+00:00", "Z")
            if already_downloaded(conn, symbol, source_hour):
                continue
            url = build_tick_url(download_cfg["base_url"], symbol, hour)
            try:
                payload = fetch_bytes(
                    url,
                    int(download_cfg["timeout_seconds"]),
                    int(download_cfg["retries"]),
                    int(download_cfg["retry_sleep_seconds"]),
                    ssl_context,
                )
                if payload is None:
                    missing_hours += 1
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO download_hours (
                            symbol, source_hour_utc, source_url, status, payload_bytes,
                            tick_count, downloaded_at_utc, error
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            symbol,
                            source_hour,
                            url,
                            "missing",
                            None,
                            0,
                            dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                            None,
                        ),
                    )
                    conn.commit()
                    continue
            except Exception as exc:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO download_hours (
                        symbol, source_hour_utc, source_url, status, payload_bytes,
                        tick_count, downloaded_at_utc, error
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        source_hour,
                        url,
                        "error",
                        None,
                        0,
                        dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                        repr(exc),
                    ),
                )
                conn.commit()
                raise

            downloaded_hours += 1
            if keep_raw_bi5:
                raw_path = raw_dir / f"{symbol}_{hour:%Y%m%d_%H}.bi5"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(payload)

            hour_tick_count = 0
            for ts, bid, ask, bid_vol, ask_vol in decode_ticks(payload, hour, price_scale):
                if len(sample_prices) < 20:
                    sample_prices.append((bid + ask) / 2.0)
                decoded_ticks += 1
                hour_tick_count += 1
                tick_batch.append(
                    (
                        symbol,
                        timestamp_ms(ts),
                        ts.isoformat().replace("+00:00", "Z"),
                        bid,
                        ask,
                        bid_vol,
                        ask_vol,
                        source_hour,
                        url,
                    )
                )
                if len(tick_batch) >= batch_insert_rows:
                    flush_tick_batch(conn, tick_batch)

            flush_tick_batch(conn, tick_batch)
            conn.execute(
                """
                INSERT OR REPLACE INTO download_hours (
                    symbol, source_hour_utc, source_url, status, payload_bytes,
                    tick_count, downloaded_at_utc, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    source_hour,
                    url,
                    "ok",
                    len(payload),
                    hour_tick_count,
                    dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                    None,
                ),
            )
            conn.commit()
    finally:
        flush_tick_batch(conn, tick_batch)

    avg_sample_price = sum(sample_prices) / len(sample_prices) if sample_prices else None
    db_tick_count = conn.execute("SELECT COUNT(*) FROM ticks WHERE symbol = ?", (symbol,)).fetchone()[0]
    min_max = conn.execute(
        "SELECT MIN(timestamp_utc), MAX(timestamp_utc) FROM ticks WHERE symbol = ?",
        (symbol,),
    ).fetchone()
    conn.close()

    manifest = output_dir / "manifest.txt"
    manifest.write_text(
        "\n".join(
            [
                f"symbol={symbol}",
                f"start_date_utc={start_date.isoformat()}",
                f"end_date_utc_exclusive={end_date.isoformat()}",
                f"price_scale={price_scale:g}",
                f"downloaded_hours={downloaded_hours}",
                f"missing_hours={missing_hours}",
                f"decoded_ticks={decoded_ticks}",
                f"sqlite_path={sqlite_path}",
                f"db_tick_count={db_tick_count}",
                f"min_timestamp_utc={min_max[0]}",
                f"max_timestamp_utc={min_max[1]}",
                f"avg_first_20_mid_price={avg_sample_price}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"sqlite_path={sqlite_path}")
    print(f"manifest={manifest}")
    print(
        f"downloaded_hours={downloaded_hours} missing_hours={missing_hours} "
        f"decoded_ticks={decoded_ticks} db_tick_count={db_tick_count}"
    )
    if avg_sample_price is not None:
        print(f"avg_first_20_mid_price={avg_sample_price:.6f}")
        if avg_sample_price < 1000 or avg_sample_price > 10000:
            print("WARNING: sample XAUUSD price is outside a broad sanity range; check decode.price_scale.")


if __name__ == "__main__":
    main()
