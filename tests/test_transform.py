import re

import pytest
import json

from datetime import date
from decimal import Decimal
from src.transform import transform_daily_records, load_raw_snapshot
from pathlib import Path


def test_transform_daily_records_converts_valid_data():
    raw_data = {
        "Meta Data": {
            "2. Symbol": "AAPL",
        },
        "Time Series (Daily)": {
            "2026-08-07": {
                "1. open": "220.0000",
                "2. high": "225.0000",
                "3. low": "218.0000",
                "4. close": "223.0000",
                "5. volume": "1500000",
            },
        },
    }

    clean_records = transform_daily_records(raw_data)

    assert len(clean_records) == 1

    assert clean_records[0] == {
        "symbol": "AAPL",
        "trade_date": date(2026, 8, 7),
        "open": Decimal("220.0000"),
        "high": Decimal("225.0000"),
        "low": Decimal("218.0000"),
        "close": Decimal("223.0000"),
        "volume": 1500000,
    }


def test_transform_daily_records_sorts_by_trade_date():
    raw_data = {
        "Meta Data": {
            "2. Symbol": "AAPL",
        },
        "Time Series (Daily)": {
            "2026-08-07": {
                "1. open": "220.0000",
                "2. high": "225.0000",
                "3. low": "218.0000",
                "4. close": "223.0000",
                "5. volume": "1500000",
            },
            "2026-08-05": {
                "1. open": "210.0000",
                "2. high": "215.0000",
                "3. low": "208.0000",
                "4. close": "213.0000",
                "5. volume": "1400000",
            },
            "2026-08-06": {
                "1. open": "215.0000",
                "2. high": "221.0000",
                "3. low": "214.0000",
                "4. close": "220.0000",
                "5. volume": "1450000",
            },
        },
    }

    clean_records = transform_daily_records(raw_data)

    trade_dates = [
        record["trade_date"]
        for record in clean_records
    ]

    assert trade_dates == [
        date(2026, 8, 5),
        date(2026, 8, 6),
        date(2026, 8, 7),
    ]


def test_transform_daily_records_rejects_missing_field():
    raw_data = {
        "Meta Data": {
            "2. Symbol": "AAPL",
        },
        "Time Series (Daily)": {
            "2026-08-07": {
                "1. open": "220.0000",
                "2. high": "225.0000",
                "3. low": "218.0000",
                "4. close": "223.0000",
            },
        },
    }

    with pytest.raises(
        ValueError,
        match="is missing fields",
    ):
        transform_daily_records(raw_data)


def test_load_raw_snapshot_loads_valid_json(
    tmp_path: Path,
):
    raw_data = {
        "Meta Data": {
            "2. Symbol": "AAPL",
        },
        "Time Series (Daily)": {
            "2026-08-07": {
                "1. open": "220.0000",
                "2. high": "225.0000",
                "3. low": "218.0000",
                "4. close": "223.0000",
                "5. volume": "1500000",
            },
        },
    }

    snapshot_path = tmp_path / "snapshot.json"

    snapshot_path.write_text(
        json.dumps(raw_data),
        encoding="utf-8",
    )

    loaded_data = load_raw_snapshot(
        snapshot_path
    )

    assert loaded_data == raw_data


def test_load_raw_snapshot_rejects_missing_file(
    tmp_path: Path,
):
    missing_path = (
        tmp_path / "missing_snapshot.json"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Raw data file was not found",
    ):
        load_raw_snapshot(missing_path)


def test_load_raw_snapshot_rejects_invalid_json(
    tmp_path: Path,
):
    snapshot_path = (
        tmp_path / "invalid_snapshot.json"
    )

    snapshot_path.write_text(
        "{this is not valid json}",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="does not contain valid JSON",
    ):
        load_raw_snapshot(snapshot_path)


def test_load_raw_snapshot_rejects_missing_required_key(
    tmp_path: Path,
):
    raw_data = {
        "Meta Data": {
            "2. Symbol": "AAPL",
        },
    }

    snapshot_path = (
        tmp_path / "missing_key_snapshot.json"
    )

    snapshot_path.write_text(
        json.dumps(raw_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Raw data is missing expected keys",
    ):
        load_raw_snapshot(snapshot_path)


def test_load_raw_snapshot_rejects_empty_time_series(
    tmp_path: Path,
):
    raw_data = {
        "Meta Data": {
            "2. Symbol": "AAPL",
        },
        "Time Series (Daily)": {},
    }

    snapshot_path = (
        tmp_path / "empty_time_series.json"
    )

    snapshot_path.write_text(
        json.dumps(raw_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="contains no records",
    ):
        load_raw_snapshot(snapshot_path)


@pytest.mark.parametrize(
    "raw_data, expected_message",
    [
        pytest.param(
            [],
            "Expected the top level of the JSON to be an object",
            id="top-level-list",
        ),
        pytest.param(
            {
                "Meta Data": "not a dictionary",
                "Time Series (Daily)": {
                    "2026-08-07": {}
                },
            },
            "'Meta Data' must contain a JSON object",
            id="metadata-not-object",
        ),
        pytest.param(
            {
                "Meta Data": {
                    "2. Symbol": "AAPL",
                },
                "Time Series (Daily)": "not a dictionary",
            },
            "'Time Series (Daily)' must contain a JSON object",
            id="time-series-not-object",
        ),
    ],
)
def test_load_raw_snapshot_rejects_invalid_structure(
    tmp_path: Path,
    raw_data,
    expected_message: str,
):
    snapshot_path = tmp_path / "snapshot.json"

    snapshot_path.write_text(
        json.dumps(raw_data),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=re.escape(expected_message),
    ):
        load_raw_snapshot(snapshot_path)


def test_load_raw_snapshot_rejects_directory(
    tmp_path: Path,
):
    directory_path = tmp_path / "not_a_file"

    directory_path.mkdir()

    with pytest.raises(
        ValueError,
        match=re.escape("Expected a file but received"),
    ):
        load_raw_snapshot(directory_path)