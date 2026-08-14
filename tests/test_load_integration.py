from datetime import date
from decimal import Decimal
from psycopg.errors import CheckViolation

import pytest
import src.load as load

pytestmark = pytest.mark.integration


TEST_DATABASE_NAME = "real_time_data_platform_test"

@pytest.fixture
def clean_test_database(
    monkeypatch,
):
    monkeypatch.setenv(
        "DB_NAME",
        TEST_DATABASE_NAME,
    )

    with load.create_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_database();"
            )

            current_database = cursor.fetchone()[0]

            assert current_database == TEST_DATABASE_NAME

            cursor.execute(
                "TRUNCATE TABLE market_data.daily_prices;"
            )

    yield

    with load.create_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE TABLE market_data.daily_prices;"
            )


def test_load_daily_prices_inserts_record(
    clean_test_database,
):
    clean_records = [
        {
            "symbol": "AAPL",
            "trade_date": date(2026, 8, 14),
            "open": Decimal("225.0000"),
            "high": Decimal("230.0000"),
            "low": Decimal("223.0000"),
            "close": Decimal("228.0000"),
            "volume": 1500000,
        },
    ]

    result = load.load_daily_prices(
        clean_records
    )

    assert result == {
        "affected_rows": 1,
        "rows_before_load": 0,
        "rows_after_load": 1,
    }

    with load.create_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    symbol,
                    trade_date,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume
                FROM market_data.daily_prices
                WHERE symbol = %s
                  AND trade_date = %s;
                """,
                (
                    "AAPL",
                    date(2026, 8, 14),
                ),
            )

            stored_record = cursor.fetchone()

    assert stored_record == (
        "AAPL",
        date(2026, 8, 14),
        Decimal("225.0000"),
        Decimal("230.0000"),
        Decimal("223.0000"),
        Decimal("228.0000"),
        1500000,
    )


def test_load_daily_prices_upserts_existing_record(
    clean_test_database,
):
    original_record = {
        "symbol": "AAPL",
        "trade_date": date(2026, 8, 14),
        "open": Decimal("225.0000"),
        "high": Decimal("230.0000"),
        "low": Decimal("223.0000"),
        "close": Decimal("228.0000"),
        "volume": 1500000,
    }

    updated_record = {
        "symbol": "AAPL",
        "trade_date": date(2026, 8, 14),
        "open": Decimal("226.0000"),
        "high": Decimal("231.0000"),
        "low": Decimal("224.0000"),
        "close": Decimal("229.0000"),
        "volume": 1750000,
    }

    first_result = load.load_daily_prices(
        [original_record]
    )

    second_result = load.load_daily_prices(
        [updated_record]
    )

    assert first_result == {
        "affected_rows": 1,
        "rows_before_load": 0,
        "rows_after_load": 1,
    }

    assert second_result == {
        "affected_rows": 1,
        "rows_before_load": 1,
        "rows_after_load": 1,
    }

    with load.create_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    symbol,
                    trade_date,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume
                FROM market_data.daily_prices
                WHERE symbol = %s
                  AND trade_date = %s;
                """,
                (
                    "AAPL",
                    date(2026, 8, 14),
                ),
            )

            stored_record = cursor.fetchone()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM market_data.daily_prices
                WHERE symbol = %s
                  AND trade_date = %s;
                """,
                (
                    "AAPL",
                    date(2026, 8, 14),
                ),
            )

            matching_row_count = cursor.fetchone()[0]

    assert stored_record == (
        "AAPL",
        date(2026, 8, 14),
        Decimal("226.0000"),
        Decimal("231.0000"),
        Decimal("224.0000"),
        Decimal("229.0000"),
        1750000,
    )

    assert matching_row_count == 1


def test_load_daily_prices_rolls_back_batch_on_constraint_violation(
    clean_test_database,
):
    clean_records = [
        {
            "symbol": "AAPL",
            "trade_date": date(2026, 8, 13),
            "open": Decimal("220.0000"),
            "high": Decimal("225.0000"),
            "low": Decimal("218.0000"),
            "close": Decimal("223.0000"),
            "volume": 1500000,
        },
        {
            "symbol": "AAPL",
            "trade_date": date(2026, 8, 14),
            "open": Decimal("223.0000"),
            "high": Decimal("228.0000"),
            "low": Decimal("221.0000"),
            "close": Decimal("226.0000"),
            "volume": -1,
        },
    ]

    with pytest.raises(
        CheckViolation
    ):
        load.load_daily_prices(
            clean_records
        )

    with load.create_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM market_data.daily_prices;
                """
            )

            row_count = cursor.fetchone()[0]

    assert row_count == 0