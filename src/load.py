import os
from typing import Any

import psycopg
from dotenv import load_dotenv

from src.transform import (
    RAW_DATA_DIR,
    find_latest_raw_snapshot,
    load_raw_snapshot,
    transform_daily_records,
)

load_dotenv()

UPSERT_DAILY_PRICES_SQL = """
    INSERT INTO market_data.daily_prices (
        symbol,
        trade_date,
        open_price,
        high_price,
        low_price,
        close_price,
        volume
    )
    VALUES (
        %(symbol)s,
        %(trade_date)s,
        %(open)s,
        %(high)s,
        %(low)s,
        %(close)s,
        %(volume)s
    )
    ON CONFLICT (symbol, trade_date)
    DO UPDATE SET
        open_price = EXCLUDED.open_price,
        high_price = EXCLUDED.high_price,
        low_price = EXCLUDED.low_price,
        close_price = EXCLUDED.close_price,
        volume = EXCLUDED.volume,
        ingested_at = CURRENT_TIMESTAMP;
"""

def get_required_environment_variable(name: str) -> str:
    """Return a required environment variable or raise a clear error."""

    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def create_database_connection() -> psycopg.Connection:
    """Create and return a connection to the PostgreSQL database."""

    return psycopg.connect(
        host=get_required_environment_variable("DB_HOST"),
        port=int(get_required_environment_variable("DB_PORT")),
        dbname=get_required_environment_variable("DB_NAME"),
        user=get_required_environment_variable("DB_USER"),
        password=get_required_environment_variable("DB_PASSWORD"),
        connect_timeout=10,
    )

def get_daily_price_count(connection: psycopg.Connection) -> int:
    """Return the total number of rows in the daily_prices table."""

    with connection.cursor() as cursor:
         cursor.execute("SELECT COUNT(*) FROM market_data.daily_prices")
         count_result = cursor.fetchone()

         if count_result is None:
             raise RuntimeError("PostgreSQL returned no daily price count.")
         
         return count_result[0]

def upsert_daily_prices(connection: psycopg.Connection, clean_records: list[dict[str, Any]]) -> int:
    """Insert new daily prices and update existing daily prices."""

    if not clean_records:
        return 0

    with connection.cursor() as cursor:
        cursor.executemany(
            UPSERT_DAILY_PRICES_SQL,
            clean_records,
        )

        return cursor.rowcount

def load_daily_prices(clean_records: list[dict[str, Any]]) -> dict[str, int]:

    """Load clean daily-price records and return load statistics."""

    if not clean_records:
        raise RuntimeError("No clean daily-price records were providing for loading.")

    with create_database_connection() as connection:
        rows_before_load = get_daily_price_count(connection)
    
        affected_rows = upsert_daily_prices(connection, clean_records)
    
        rows_after_load = get_daily_price_count(connection)

    return {
        "affected_rows": affected_rows,
        "rows_before_load": rows_before_load,
        "rows_after_load": rows_after_load,
    }

def load_latest_daily_prices() -> None:
    """Transform the latest raw snapshot and load it into PostgreSQL."""

    latest_snapshot_path = find_latest_raw_snapshot(RAW_DATA_DIR)

    raw_data = load_raw_snapshot(latest_snapshot_path)

    clean_records = transform_daily_records(raw_data)

    load_result = load_daily_prices(clean_records)

    print(f"Loaded raw snapshot: {latest_snapshot_path}")
    print(f"Clean records prepared: {len(clean_records)}")
    print(
        "Rows inserted or updated: "
        f"{load_result['affected_rows']}"
    )
    print(
        "Table rows before load: "
        f"{load_result['rows_before_load']}"
    )
    print(
        "Table rows after load: "
        f"{load_result['rows_after_load']}"
    )


if __name__ == "__main__":
    load_latest_daily_prices()
