-- DuckDB CLI: duckdb output/ibkr_us_equity.duckdb < inspect_ibkr_l1_trade.sql
.mode box

SELECT * FROM raw._ingest_partitions ORDER BY partition_date;

SELECT
  _symbol,
  min(_partition_date) AS first_date,
  max(_partition_date) AS last_date,
  count(*) AS rows,
  count(DISTINCT _partition_date) AS covered_dates,
  count(DISTINCT filename) AS source_files
FROM raw.ibkr_stock_us_l1_trade
GROUP BY ALL;

DESCRIBE raw.ibkr_stock_us_l1_trade;

SELECT *
FROM raw.ibkr_stock_us_l1_trade
ORDER BY _partition_date, filename
LIMIT 20;
