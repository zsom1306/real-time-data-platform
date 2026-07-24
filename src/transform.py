import json
from pathlib import Path
from typing import Any

REQUIRED_KEYS = ["Meta Data", "Time Series (Daily)"]
RAW_DATA_DIR = Path("data") / "raw" / "alpha_vantage" / "daily"

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

def main() -> None:
    latest_snapshot = find_latest_raw_snapshot(RAW_DATA_DIR)
    raw_data = load_raw_snapshot(latest_snapshot)

    record_count = len(raw_data["Time Series (Daily)"])

    print(f"Loaded raw snapshot: {latest_snapshot}")
    print(f"Daily records found: {record_count}")

if __name__ == "__main__":
    main()