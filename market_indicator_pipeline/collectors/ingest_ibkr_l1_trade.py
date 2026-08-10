#!/usr/bin/env python3
"""Incrementally ingest partitioned IBKR L1 trades from RustFS into DuckDB."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
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


def parse_csv_list(value: str | None, fallback: list[str]) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()] if value else fallback


def dates_between(start: str, end: str) -> list[str]:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError("date-start must be <= date-end")
    return [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]


def ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def resolve_db_path(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (config_path.parent / path).resolve()


def source_glob(cfg: dict[str, Any], symbol: str, data_type: str, day: str) -> str:
    src = cfg["source"]
    extension = {"csv_zst": "csv.zst", "parquet": "parquet"}[src["format"]]
    suffix = src["path_template"].format(
        source=src["source"], asset_type=src["asset_type"], market=src["market"],
        symbol=symbol, data_type=data_type, date=day, extension=extension,
    )
    return f"{src['root'].rstrip('/')}/{suffix.lstrip('/')}"


def read_relation(cfg: dict[str, Any], path: str) -> str:
    if cfg["source"]["format"] == "parquet":
        return f"read_parquet({literal(path)}, union_by_name=true, filename=true)"
    csv_cfg = cfg["ingest"]["csv"]
    return (
        f"read_csv({literal(path)}, header={str(bool(csv_cfg['header'])).lower()}, "
        f"auto_detect={str(bool(csv_cfg['auto_detect'])).lower()}, "
        f"sample_size={int(csv_cfg['sample_size'])}, "
        f"ignore_errors={str(bool(csv_cfg['ignore_errors'])).lower()}, "
        "union_by_name=true, filename=true)"
    )


def configure_s3(con: duckdb.DuckDBPyConnection, cfg: dict[str, Any]) -> None:
    s3 = cfg["rustfs"]
    access = os.getenv(s3["access_key_env"])
    secret = os.getenv(s3["secret_key_env"])
    if not access or not secret:
        raise RuntimeError(f"missing {s3['access_key_env']} or {s3['secret_key_env']}")
    endpoint = os.getenv(s3["endpoint_env"], s3["default_endpoint"])
    region = os.getenv(s3["region_env"], s3["default_region"])
    con.execute("INSTALL httpfs; LOAD httpfs")
    con.execute(
        "CREATE OR REPLACE SECRET rustfs_secret (TYPE s3, "
        f"KEY_ID {literal(access)}, SECRET {literal(secret)}, REGION {literal(region)}, "
        f"ENDPOINT {literal(endpoint)}, URL_STYLE {literal(s3['url_style'])}, "
        f"USE_SSL {str(bool(s3['use_ssl'])).lower()})"
    )


def ensure_metadata(con: duckdb.DuckDBPyConnection, schema: str) -> None:
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {ident(schema)}")
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {ident(schema)}._ingest_partitions (
            target_table VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            data_type VARCHAR NOT NULL,
            partition_date DATE NOT NULL,
            source_glob VARCHAR NOT NULL,
            row_count UBIGINT NOT NULL,
            min_source_filename VARCHAR,
            max_source_filename VARCHAR,
            ingested_at_utc TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (target_table, symbol, data_type, partition_date)
        )
    """)


def table_exists(con: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
    return bool(con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema=? AND table_name=?",
        [schema, table],
    ).fetchone()[0])


def add_new_columns(con: duckdb.DuckDBPyConnection, schema: str, table: str, select_sql: str) -> None:
    existing = {row[0].lower() for row in con.execute(f"DESCRIBE {ident(schema)}.{ident(table)}").fetchall()}
    for name, dtype, *_ in con.execute(f"DESCRIBE SELECT * FROM ({select_sql})").fetchall():
        if name.lower() not in existing:
            con.execute(f"ALTER TABLE {ident(schema)}.{ident(table)} ADD COLUMN {ident(name)} {dtype}")


def ingest_day(con: duckdb.DuckDBPyConnection, cfg: dict[str, Any], symbol: str, data_type: str, day: str) -> int:
    schema, table = cfg["duckdb"]["schema"], cfg["duckdb"]["table"]
    path = source_glob(cfg, symbol, data_type, day)
    relation = read_relation(cfg, path)
    select_sql = (
        f"SELECT *, {literal(cfg['source']['source'])} AS _source, "
        f"{literal(cfg['source']['asset_type'])} AS _asset_type, "
        f"{literal(cfg['source']['market'])} AS _market, {literal(symbol)} AS _symbol, "
        f"{literal(data_type)} AS _data_type, DATE {literal(day)} AS _partition_date "
        f"FROM {relation}"
    )
    try:
        count = int(con.execute(f"SELECT count(*) FROM ({select_sql})").fetchone()[0])
    except duckdb.IOException as exc:
        if cfg["ingest"]["allow_missing_dates"] and any(x in str(exc).lower() for x in ("no files", "not found", "404")):
            print(f"WARN missing date={day} path={path}", flush=True)
            return 0
        raise
    if count == 0:
        print(f"WARN empty date={day} path={path}", flush=True)
        return 0

    con.execute("BEGIN")
    try:
        if not table_exists(con, schema, table):
            con.execute(f"CREATE TABLE {ident(schema)}.{ident(table)} AS {select_sql} LIMIT 0")
        else:
            add_new_columns(con, schema, table, select_sql)
        con.execute(
            f"DELETE FROM {ident(schema)}.{ident(table)} WHERE _symbol=? AND _data_type=? AND _partition_date=?",
            [symbol, data_type, day],
        )
        con.execute(f"INSERT INTO {ident(schema)}.{ident(table)} BY NAME {select_sql}")
        filenames = con.execute(
            f"SELECT min(filename), max(filename) FROM {ident(schema)}.{ident(table)} "
            "WHERE _symbol=? AND _data_type=? AND _partition_date=?",
            [symbol, data_type, day],
        ).fetchone()
        con.execute(
            f"INSERT OR REPLACE INTO {ident(schema)}._ingest_partitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [table, symbol, data_type, day, path, count, filenames[0], filenames[1], datetime.now(timezone.utc)],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    print(f"OK symbol={symbol} data_type={data_type} date={day} rows={count}", flush=True)
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--tokens", help="comma-separated symbols")
    parser.add_argument("--date-start")
    parser.add_argument("--date-end")
    parser.add_argument("--markets", help="must match configured market")
    parser.add_argument("--max-workers", type=int)
    parser.add_argument("--output-dir", help="override directory containing the DuckDB file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    cfg = load_config(config_path)
    symbols = parse_csv_list(args.tokens, cfg["source"]["symbols"])
    start = args.date_start or cfg["date_range"]["start"]
    end = args.date_end or cfg["date_range"]["end"]
    markets = parse_csv_list(args.markets, [cfg["source"]["market"]])
    if markets != [cfg["source"]["market"]]:
        raise ValueError(f"markets override {markets} does not match configured path market={cfg['source']['market']}")
    max_workers = args.max_workers or cfg["ingest"]["max_workers"]
    if max_workers != 1:
        raise ValueError("DuckDB single-writer ingest currently requires --max-workers 1")
    db_path = resolve_db_path(config_path, cfg["duckdb"]["path"])
    if args.output_dir:
        db_path = Path(args.output_dir).expanduser().resolve() / db_path.name
    days = dates_between(start, end)
    scope = {
        "symbols": symbols, "source": cfg["source"]["source"], "asset_type": cfg["source"]["asset_type"],
        "market": markets, "data_types": cfg["source"]["data_types"], "date_start": start, "date_end": end,
        "timezone": cfg["source"]["timezone"], "timestamp_basis": cfg["source"]["timestamp_basis"],
        "format": cfg["source"]["format"], "duckdb": str(db_path), "max_workers": max_workers,
        "sample_glob": source_glob(cfg, symbols[0], cfg["source"]["data_types"][0], days[0]),
    }
    print(json.dumps(scope, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = resolve_db_path(config_path, cfg["duckdb"]["temp_directory"])
    temp_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(f"SET threads={int(cfg['duckdb']['threads'])}")
        con.execute(f"SET memory_limit={literal(cfg['duckdb']['memory_limit'])}")
        con.execute(f"SET temp_directory={literal(str(temp_dir))}")
        configure_s3(con, cfg)
        ensure_metadata(con, cfg["duckdb"]["schema"])
        total = 0
        for symbol in symbols:
            for data_type in cfg["source"]["data_types"]:
                for day in days:
                    total += ingest_day(con, cfg, symbol, data_type, day)
        print(f"DONE rows={total} database={db_path}", flush=True)
    finally:
        con.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
