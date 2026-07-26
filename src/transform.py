import json
from pathlib import Path
from typing import Any
from datetime import date
from decimal import Decimal, InvalidOperation

REQUIRED_KEYS = ["Meta Data", "Time Series (Daily)"]
RAW_DATA_DIR = Path("data") / "raw" / "alpha_vantage" / "daily"
REQUIRED_DAILY_FIELDS = [
    "1. open",
    "2. high",
    "3. low",
    "4. close",
    "5. volume",
]

def load_raw_snapshot(file_path: Path) -> dict[str, Any]:
    """"Load and validate one raw Alpha Vantage JSON snapshot."""

    if not file_path.exists():
        raise FileNotFoundError(f"Raw data file was not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Expected a file but received: {file_path}")
    
    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Raw data file does not contain valid JSON: {file_path}"
        ) from error
    
    if not isinstance(data, dict):
        raise ValueError("Expected the top level of the JSON to be an object")
    
    missing_keys = [
        key for key in REQUIRED_KEYS
        if key not in data
    ]

    if missing_keys:
        raise ValueError(f"Raw data is missing expected keys: {missing_keys}")
    
    if not isinstance(data["Meta Data"], dict):
        raise ValueError("'Meta Data' must contain a JSON object")
    
    time_series = data["Time Series (Daily)"]

    if not isinstance(time_series, dict):
        raise ValueError("'Time Series (Daily)' must contain a JSON object")
    
    if not time_series:
        raise ValueError("'Time Series (Daily)' contains no records")
    
    return data

def find_latest_raw_snapshot(raw_data_dir: Path) -> Path:
    """Find the most recently created raw JSON snapshot."""

    if not raw_data_dir.exists():
        raise FileNotFoundError(f"Raw data directory was not found: {raw_data_dir}")
    
    snapshot_paths = list(raw_data_dir.glob("*.json"))

    if not snapshot_paths:
        raise FileNotFoundError(f"No raw JSON snapshots were found in: {raw_data_dir}")
    
    latest_snapshot = max(
        snapshot_paths,
        key=lambda path: path.stat().st_mtime,
    )

    return latest_snapshot

def transform_daily_records(raw_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert raw Alpha Vantage daily data into clean records."""

    metadata = raw_data["Meta Data"]
    time_series = raw_data["Time Series (Daily)"]

    symbol = metadata.get("2. Symbol")

    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("Metadata does not contain a valid stock symbol")

    clean_records = []

    for trade_date_text, daily_values in time_series.items():
        if not isinstance(daily_values, dict):
            raise ValueError(f"Daily record for {trade_date_text} must be a JSON object")

        missing_fields = [
            field for field in REQUIRED_DAILY_FIELDS
            if field not in daily_values
        ]

        if missing_fields:
            raise ValueError(f"Daily record for {trade_date_text} is missing fields: {missing_fields}")

        try:
            trade_date = date.fromisoformat(trade_date_text)
            open_price = Decimal(daily_values["1. open"])
            high_price = Decimal(daily_values["2. high"])
            low_price = Decimal(daily_values["3. low"])
            close_price = Decimal(daily_values["4. close"])
            volume = int(daily_values["5. volume"])
        except (ValueError, TypeError, InvalidOperation) as error:
            raise ValueError(
                f"Daily record for {trade_date_text} contained an invalid value"
            ) from error

        if min(open_price, high_price, low_price, close_price) <= 0:
            raise ValueError(f"Daily record for {trade_date_text} contains a non-positive price")

        if high_price < max(open_price, low_price, close_price):
            raise ValueError(f"Daily record for {trade_date_text} has an invalid high price")

        if low_price > min(open_price, high_price, close_price):
            raise ValueError(f"Daily record for {trade_date_text} has an invalid low price")

        if volume < 0:
            raise ValueError(f"Daily record for {trade_date_text} contains negative volume")

        clean_record = {
            "symbol": symbol.upper(),
            "trade_date": trade_date,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
        }

        clean_records.append(clean_record)

    clean_records.sort(
        key=lambda record: record["trade_date"]
    )

    return clean_records

def main() -> None:
    latest_snapshot = find_latest_raw_snapshot(RAW_DATA_DIR)
    raw_data = load_raw_snapshot(latest_snapshot)
    clean_records = transform_daily_records(raw_data)

    print(f"Loaded raw snapshot: {latest_snapshot}")
    print(f"Clean records created: {len(clean_records)}")
    print(f"Oldest record: {clean_records[0]}")
    print(f"Newest record: {clean_records[-1]}")


if __name__ == "__main__":
    main()