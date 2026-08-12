from datetime import date
from decimal import Decimal

import pytest

import src.load as load

def test_get_required_environment_variable_returns_value(
    monkeypatch,
):
    monkeypatch.setenv(
        "TEST_DATABASE_SETTING",
        "test-value",
    )

    result = load.get_required_environment_variable(
        "TEST_DATABASE_SETTING"
    )

    assert result == "test-value"


def test_get_required_environment_variable_rejects_missing_value(
    monkeypatch,
):
    monkeypatch.delenv(
        "TEST_DATABASE_SETTING",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="TEST_DATABASE_SETTING",
    ):
        load.get_required_environment_variable(
            "TEST_DATABASE_SETTING"
        )


@pytest.mark.parametrize(
    "invalid_value",
    [
        "",
        "   ",
    ],
)
def test_get_required_environment_variable_rejects_blank_value(
    monkeypatch,
    invalid_value: str,
):
    monkeypatch.setenv(
        "TEST_DATABASE_SETTING",
        invalid_value,
    )

    with pytest.raises(
        RuntimeError,
        match="TEST_DATABASE_SETTING",
    ):
        load.get_required_environment_variable(
            "TEST_DATABASE_SETTING"
        )


def test_get_daily_price_count_returns_count():
    class FakeCursor:
        def __init__(self):
            self.executed_query = None

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            pass

        def execute(self, query):
            self.executed_query = query

        def fetchone(self):
            return (103,)

    class FakeConnection:
        def __init__(self):
            self.fake_cursor = FakeCursor()

        def cursor(self):
            return self.fake_cursor

    connection = FakeConnection()

    result = load.get_daily_price_count(
        connection
    )

    assert result == 103

    assert "COUNT(*)" in (
        connection.fake_cursor.executed_query
    )

    assert "market_data.daily_prices" in (
        connection.fake_cursor.executed_query
    )


def test_upsert_daily_prices_returns_zero_for_empty_records():
    class FakeConnection:
        def cursor(self):
            pytest.fail(
                "A cursor should not be created "
                "when there are no records"
            )

    connection = FakeConnection()

    result = load.upsert_daily_prices(
        connection,
        [],
    )

    assert result == 0


def test_upsert_daily_prices_executes_batch():
    clean_records = [
        {
            "symbol": "AAPL",
            "trade_date": date(2026, 8, 11),
            "open": Decimal("220.0000"),
            "high": Decimal("225.0000"),
            "low": Decimal("218.0000"),
            "close": Decimal("223.0000"),
            "volume": 1500000,
        },
        {
            "symbol": "AAPL",
            "trade_date": date(2026, 8, 12),
            "open": Decimal("223.0000"),
            "high": Decimal("228.0000"),
            "low": Decimal("221.0000"),
            "close": Decimal("226.0000"),
            "volume": 1700000,
        },
    ]

    class FakeCursor:
        def __init__(self):
            self.executed_query = None
            self.executed_records = None
            self.rowcount = 2

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            pass

        def executemany(
            self,
            query,
            records,
        ):
            self.executed_query = query
            self.executed_records = records

    class FakeConnection:
        def __init__(self):
            self.fake_cursor = FakeCursor()

        def cursor(self):
            return self.fake_cursor

    connection = FakeConnection()

    affected_rows = load.upsert_daily_prices(
        connection,
        clean_records,
    )

    assert affected_rows == 2

    assert (
        connection.fake_cursor.executed_query
        == load.UPSERT_DAILY_PRICES_SQL
    )

    assert (
        connection.fake_cursor.executed_records
        == clean_records
    )


def test_load_daily_prices_coordinates_load(
    monkeypatch,
):
    clean_records = [
        {
            "symbol": "AAPL",
            "trade_date": date(2026, 8, 12),
            "open": Decimal("223.0000"),
            "high": Decimal("228.0000"),
            "low": Decimal("221.0000"),
            "close": Decimal("226.0000"),
            "volume": 1700000,
        },
    ]

    call_log = []

    class FakeConnection:
        def __init__(self):
            self.entered = False
            self.exited = False

        def __enter__(self):
            self.entered = True
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            self.exited = True

    fake_connection = FakeConnection()

    count_results = iter([100, 101])

    def fake_create_database_connection():
        call_log.append(
            "create_connection"
        )

        return fake_connection

    def fake_get_daily_price_count(connection):
        assert connection is fake_connection

        call_log.append(
            "count"
        )

        return next(count_results)

    def fake_upsert_daily_prices(
        connection,
        records,
    ):
        assert connection is fake_connection
        assert records == clean_records

        call_log.append(
            "upsert"
        )

        return 1

    monkeypatch.setattr(
        load,
        "create_database_connection",
        fake_create_database_connection,
    )

    monkeypatch.setattr(
        load,
        "get_daily_price_count",
        fake_get_daily_price_count,
    )

    monkeypatch.setattr(
        load,
        "upsert_daily_prices",
        fake_upsert_daily_prices,
    )

    result = load.load_daily_prices(
        clean_records
    )

    assert result == {
        "affected_rows": 1,
        "rows_before_load": 100,
        "rows_after_load": 101,
    }

    assert call_log == [
        "create_connection",
        "count",
        "upsert",
        "count",
    ]

    assert fake_connection.entered is True
    assert fake_connection.exited is True


def test_load_daily_prices_rejects_empty_records(
    monkeypatch,
):
    def fail_if_called():
        pytest.fail(
            "Database connection should not be "
            "created for empty records"
        )

    monkeypatch.setattr(
        load,
        "create_database_connection",
        fail_if_called,
    )

    with pytest.raises(
        RuntimeError,
        match="No clean daily-price records",
    ):
        load.load_daily_prices([])


def test_load_latest_daily_prices_coordinates_pipeline(
    monkeypatch,
):
    fake_snapshot_path = object()
    fake_raw_data = object()
    fake_clean_records = object()

    call_log = []

    def fake_find_latest_raw_snapshot(
        raw_data_dir,
    ):
        assert raw_data_dir is load.RAW_DATA_DIR

        call_log.append(
            "find_snapshot"
        )

        return fake_snapshot_path

    def fake_load_raw_snapshot(
        snapshot_path,
    ):
        assert snapshot_path is fake_snapshot_path

        call_log.append(
            "load_snapshot"
        )

        return fake_raw_data

    def fake_transform_daily_records(
        raw_data,
    ):
        assert raw_data is fake_raw_data

        call_log.append(
            "transform"
        )

        return fake_clean_records

    def fake_load_daily_prices(
        clean_records,
    ):
        assert clean_records is fake_clean_records

        call_log.append(
            "load"
        )

        return {
            "affected_rows": 1,
            "rows_before_load": 100,
            "rows_after_load": 101,
        }

    monkeypatch.setattr(
        load,
        "find_latest_raw_snapshot",
        fake_find_latest_raw_snapshot,
    )

    monkeypatch.setattr(
        load,
        "load_raw_snapshot",
        fake_load_raw_snapshot,
    )

    monkeypatch.setattr(
        load,
        "transform_daily_records",
        fake_transform_daily_records,
    )

    monkeypatch.setattr(
        load,
        "load_daily_prices",
        fake_load_daily_prices,
    )

    load.load_latest_daily_prices()

    assert call_log == [
        "find_snapshot",
        "load_snapshot",
        "transform",
        "load",
    ]