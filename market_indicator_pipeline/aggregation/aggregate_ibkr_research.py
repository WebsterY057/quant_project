#!/usr/bin/env python3
"""Aggregate IBKR L1 trade events into 1-minute and 5-minute bars."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import duckdb
import yaml


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"config is not a mapping: {path}")
    return config


def ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def resolve_path(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (config_path.parent / path).resolve()


def safe_filter(value: str) -> str:
    if any(token in value for token in (";", "--", "/*", "*/")):
        raise ValueError("unsafe volume_event_filter")
    return value


def build_bars(
    con: duckdb.DuckDBPyConnection,
    cfg: dict[str, Any],
    label: str,
    interval: str,
) -> tuple[str, int]:
    src, out = cfg["input"], cfg["output"]
    source_table = f"{ident(src['schema'])}.{ident(src['table'])}"
    table_name = f"{out['table_prefix']}_{label}"
    target_table = f"{ident(out['schema'])}.{ident(table_name)}"
    ts = ident(src["event_time_column"])
    price = ident(src["price_column"])
    size = ident(src["size_column"])
    volume_filter = safe_filter(src["volume_event_filter"])

    con.execute(f"DROP TABLE IF EXISTS {target_table}")
    con.execute(f"""
        CREATE TABLE {target_table} AS
        WITH source_rows AS (
            SELECT
                symbol,
                {ts} AS event_time,
                {price}::DOUBLE AS price,
                {size}::DOUBLE AS size,
                trigger_field
            FROM {source_table}
            WHERE symbol = {literal(src['symbol'])}
              AND _partition_date BETWEEN
                  DATE {literal(src['date_start'])}
                  AND DATE {literal(src['date_end'])}
              AND event = 'l1_trade'
              AND {ts} IS NOT NULL
              AND {price} > 0
              AND {size} >= 0
        ), bucketed AS (
            SELECT
                *,
                time_bucket(INTERVAL {literal(interval)}, event_time) AS bar_start_utc
            FROM source_rows
        )
        SELECT
            symbol,
            {literal(label)} AS interval,
            bar_start_utc,
            bar_start_utc + INTERVAL {literal(interval)} AS bar_end_utc,
            arg_min(price, event_time) AS open,
            max(price) AS high,
            min(price) AS low,
            arg_max(price, event_time) AS close,
            coalesce(sum(size) FILTER (WHERE {volume_filter}), 0) AS volume,
            sum(price * size) FILTER (WHERE ({volume_filter}) AND size > 0)
                / nullif(sum(size) FILTER (WHERE ({volume_filter}) AND size > 0), 0)
                AS vwap,
            count(*) FILTER (WHERE {volume_filter}) AS trade_count,
            count(*) AS source_event_count,
            min(event_time) AS first_event_time,
            max(event_time) AS last_event_time
        FROM bucketed
        GROUP BY symbol, bar_start_utc
        ORDER BY bar_start_utc
    """)
    count = int(con.execute(f"SELECT count(*) FROM {target_table}").fetchone()[0])
    return table_name, count


def moving_average(values: list[float | None], period: int, method: str) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    normalized = method.upper()
    if normalized == "LWMA":
        weight_sum = period * (period + 1) / 2
        for index in range(period - 1, len(values)):
            window = values[index - period + 1:index + 1]
            if any(value is None for value in window):
                continue
            result[index] = sum(float(window[-1-offset]) * (period-offset) for offset in range(period)) / weight_sum
        return result
    if normalized == "SMMA":
        valid_count = 0
        running_sum = 0.0
        for index, value in enumerate(values):
            if value is None:
                valid_count, running_sum = 0, 0.0
                continue
            running_sum += float(value)
            valid_count += 1
            if valid_count == period and (index == 0 or result[index - 1] is None):
                result[index] = running_sum / period
            elif valid_count > period:
                result[index] = (float(result[index - 1]) * (period - 1) + float(value)) / period
        return result
    raise ValueError(f"unsupported moving-average method: {method}")


def smooth_ohlc(values: list[tuple[float, float, float, float] | None], period: int, method: str) -> list[tuple[float, float, float, float] | None]:
    columns = [moving_average([row[index] if row else None for row in values], period, method) for index in range(4)]
    return [None if any(column[index] is None for column in columns) else tuple(float(column[index]) for column in columns) for index in range(len(values))]


def heiken_ashi(rows: list[tuple[Any, ...]], cfg: dict[str, Any]) -> list[tuple[float | None, float | None, float | None, float | None]]:
    raw = [tuple(map(float, row[2:6])) for row in rows]
    first = smooth_ohlc(raw, int(cfg["ma1_period"]), str(cfg["ma1_method"]))
    ha: list[tuple[float, float, float, float] | None] = [None] * len(rows)
    for index, item in enumerate(first):
        if item is None:
            continue
        open_, high, low, close = item
        ha_close = (open_ + high + low + close) / 4.0
        previous = ha[index - 1] if index else None
        ha_open = (previous[0] + previous[3]) / 2.0 if previous else (open_ + close) / 2.0
        ha[index] = (ha_open, max(high, ha_open, ha_close), min(low, ha_open, ha_close), ha_close)
    second = smooth_ohlc(ha, int(cfg["ma2_period"]), str(cfg["ma2_method"]))
    return [item if item else (None, None, None, None) for item in second]


def parabolic_sar(
    rows: list[tuple[Any, ...]], step: float, maximum: float
) -> list[tuple[float, str]]:
    if not rows:
        return []
    if len(rows) == 1:
        return [(float(rows[0][4]), "long")]
    highs = [float(row[3]) for row in rows]
    lows = [float(row[4]) for row in rows]
    closes = [float(row[5]) for row in rows]
    rising = closes[1] >= closes[0]
    sar = lows[0] if rising else highs[0]
    extreme = max(highs[0], highs[1]) if rising else min(lows[0], lows[1])
    acceleration = step
    result: list[tuple[float, str]] = [(sar, "long" if rising else "short")]

    for index in range(1, len(rows)):
        candidate = sar + acceleration * (extreme - sar)
        if rising:
            candidate = min(candidate, lows[index - 1])
            if index > 1:
                candidate = min(candidate, lows[index - 2])
            if lows[index] < candidate:
                rising = False
                candidate = extreme
                extreme = lows[index]
                acceleration = step
            elif highs[index] > extreme:
                extreme = highs[index]
                acceleration = min(maximum, acceleration + step)
        else:
            candidate = max(candidate, highs[index - 1])
            if index > 1:
                candidate = max(candidate, highs[index - 2])
            if highs[index] > candidate:
                rising = True
                candidate = extreme
                extreme = highs[index]
                acceleration = step
            elif lows[index] < extreme:
                extreme = lows[index]
                acceleration = min(maximum, acceleration + step)
        sar = candidate
        result.append((sar, "long" if rising else "short"))
    return result


def zigzag(
    rows: list[tuple[Any, ...]],
    depth: int,
    deviation_points: int,
    backstep: int,
    point_size: float,
    show_unconfirmed: bool,
    live_reversal_percent: float,
    live_reversal_abs: float,
) -> tuple[list[tuple[float | None, str | None]], list[tuple[float | None, str | None]]]:
    """Match the existing gold dashboard's confirmed and live ZigZag."""
    size = len(rows)
    highs = [float(row[3]) for row in rows]
    lows = [float(row[4]) for row in rows]
    deviation = deviation_points * point_size
    confirmed: list[tuple[int, float, str]] = []
    confirmed_end = size - 1 - depth
    for index in range(max(0, confirmed_end + 1)):
        left, right = max(0, index - depth), min(size - 1, index + depth)
        candidates: list[tuple[int, float, str]] = []
        if highs[index] >= max(highs[left:right + 1]): candidates.append((index, highs[index], "high"))
        if lows[index] <= min(lows[left:right + 1]): candidates.append((index, lows[index], "low"))
        for candidate in candidates:
            if not confirmed:
                confirmed.append(candidate); continue
            previous = confirmed[-1]
            if abs(candidate[1] - previous[1]) < deviation: continue
            if candidate[2] == previous[2]:
                more_extreme = candidate[1] > previous[1] if candidate[2] == "high" else candidate[1] < previous[1]
                if more_extreme or candidate[0] - previous[0] <= backstep: confirmed[-1] = candidate
            else:
                confirmed.append(candidate)
    pivots: list[tuple[float | None, str | None]] = [(None, None) for _ in rows]
    live: list[tuple[float | None, str | None]] = [(None, None) for _ in rows]
    for index, value, kind in confirmed: pivots[index] = (value, kind)
    if show_unconfirmed and confirmed:
        last_index, last_value, last_kind = confirmed[-1]
        live_kind = "low" if last_kind == "high" else "high"
        candidates = [(index, lows[index] if live_kind == "low" else highs[index]) for index in range(last_index + 1, size)]
        if candidates:
            live_index, live_value = min(candidates, key=lambda x: x[1]) if live_kind == "low" else max(candidates, key=lambda x: x[1])
            threshold = max(deviation, abs(last_value) * live_reversal_percent / 100.0, live_reversal_abs)
            if abs(live_value - last_value) >= threshold:
                live[last_index] = (last_value, last_kind)
                live[live_index] = (live_value, live_kind)
    return pivots, live


def add_mt4_indicators(
    con: duckdb.DuckDBPyConnection, cfg: dict[str, Any], table_name: str
) -> None:
    out = cfg["output"]
    table = f"{ident(out['schema'])}.{ident(table_name)}"
    rows = con.execute(
        f"SELECT symbol, epoch_us(bar_start_utc), open, high, low, close "
        f"FROM {table} ORDER BY symbol, bar_start_utc"
    ).fetchall()
    print(f"INDICATOR_START table={out['schema']}.{table_name} bars={len(rows)}", flush=True)
    con.execute(f"ALTER TABLE {table} ADD COLUMN ha_open DOUBLE")
    con.execute(f"ALTER TABLE {table} ADD COLUMN ha_high DOUBLE")
    con.execute(f"ALTER TABLE {table} ADD COLUMN ha_low DOUBLE")
    con.execute(f"ALTER TABLE {table} ADD COLUMN ha_close DOUBLE")
    con.execute(f"ALTER TABLE {table} ADD COLUMN psar DOUBLE")
    con.execute(f"ALTER TABLE {table} ADD COLUMN psar_trend VARCHAR")
    con.execute(f"ALTER TABLE {table} ADD COLUMN zigzag DOUBLE")
    con.execute(f"ALTER TABLE {table} ADD COLUMN zigzag_type VARCHAR")
    con.execute(f"ALTER TABLE {table} ADD COLUMN zigzag_live DOUBLE")
    con.execute(f"ALTER TABLE {table} ADD COLUMN zigzag_live_type VARCHAR")

    psar_cfg = cfg["indicators"]["parabolic_sar"]
    zigzag_cfg = cfg["indicators"]["zigzag"]
    ha_values = heiken_ashi(rows, cfg["indicators"]["heiken_ashi"])
    psar_values = parabolic_sar(rows, float(psar_cfg["step"]), float(psar_cfg["maximum"]))
    zigzag_values, zigzag_live_values = zigzag(
        rows,
        int(zigzag_cfg["depth"]),
        int(zigzag_cfg["deviation_points"]),
        int(zigzag_cfg["backstep"]),
        float(zigzag_cfg["point_size"]),
        bool(zigzag_cfg["show_unconfirmed"]),
        float(zigzag_cfg["live_reversal_percent"]),
        float(zigzag_cfg["live_reversal_abs"]),
    )
    updates = []
    for row, ha, psar_value, zigzag_value, zigzag_live_value in zip(rows, ha_values, psar_values, zigzag_values, zigzag_live_values):
        updates.append((*ha, *psar_value, *zigzag_value, *zigzag_live_value, row[0], row[1]))
    temp_table = "_mt4_indicator_values"
    con.execute(f"DROP TABLE IF EXISTS {ident(temp_table)}")
    con.execute(f"""
        CREATE TEMP TABLE {ident(temp_table)} (
            ha_open DOUBLE,
            ha_high DOUBLE,
            ha_low DOUBLE,
            ha_close DOUBLE,
            psar DOUBLE,
            psar_trend VARCHAR,
            zigzag DOUBLE,
            zigzag_type VARCHAR,
            zigzag_live DOUBLE,
            zigzag_live_type VARCHAR,
            symbol VARCHAR,
            bar_start_us BIGINT
        )
    """)
    print(f"INDICATOR_CALCULATED table={out['schema']}.{table_name}", flush=True)
    con.executemany(
        f"INSERT INTO {ident(temp_table)} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        updates,
    )
    print(f"INDICATOR_STAGED table={out['schema']}.{table_name} rows={len(updates)}", flush=True)
    con.execute(f"""
        UPDATE {table} AS target SET
          ha_open=source.ha_open,
          ha_high=source.ha_high,
          ha_low=source.ha_low,
          ha_close=source.ha_close,
          psar=source.psar,
          psar_trend=source.psar_trend,
          zigzag=source.zigzag,
          zigzag_type=source.zigzag_type,
          zigzag_live=source.zigzag_live,
          zigzag_live_type=source.zigzag_live_type
        FROM {ident(temp_table)} AS source
        WHERE target.symbol=source.symbol
          AND epoch_us(target.bar_start_utc)=source.bar_start_us
    """)
    con.execute(f"DROP TABLE {ident(temp_table)}")
    print(f"INDICATOR_DONE table={out['schema']}.{table_name}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--duckdb-path")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    cfg = load_config(config_path)
    db_path = resolve_path(
        config_path,
        args.duckdb_path or cfg["input"]["duckdb_path"],
    )
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    export_dir = resolve_path(config_path, cfg["output"]["export_dir"])
    export_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))
    try:
        con.execute(f"SET TimeZone={literal(cfg['aggregation']['timezone'])}")
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {ident(cfg['output']['schema'])}")

        for item in cfg["aggregation"]["intervals"]:
            print(f"BAR_START interval={item['label']}", flush=True)
            table_name, row_count = build_bars(
                con,
                cfg,
                item["label"],
                item["duckdb_interval"],
            )
            add_mt4_indicators(con, cfg, table_name)
            target = f"{ident(cfg['output']['schema'])}.{ident(table_name)}"
            parquet = export_dir / f"{table_name}.parquet"
            csv_file = export_dir / f"{table_name}.csv"
            con.execute(
                f"COPY {target} TO {literal(str(parquet))} "
                "(FORMAT PARQUET, COMPRESSION ZSTD)"
            )
            con.execute(
                f"COPY {target} TO {literal(str(csv_file))} "
                "(FORMAT CSV, HEADER TRUE)"
            )
            print(
                f"OK interval={item['label']} rows={row_count} "
                f"table={cfg['output']['schema']}.{table_name}",
                flush=True,
            )

        print(f"DONE database={db_path} export_dir={export_dir}", flush=True)
    finally:
        con.close()


if __name__ == "__main__":
    main()
