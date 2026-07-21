import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://www.alphavantage.co/query"

RAW_DATA_DIR = Path("data") / "raw" / "alpha_vantage" / "daily"

load_dotenv()

api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

if not api_key:
    raise ValueError("ALPHA_VANTAGE_API_KEY was not found")


symbol = "AAPL"  

params = {
    "function": "TIME_SERIES_DAILY",
    "symbol": symbol,
    "outputsize": "compact",
    "datatype": "json",
    "apikey": api_key
}

response = requests.get(
    BASE_URL,
    params=params,
    timeout=30,
)

response.raise_for_status()

data = response.json()

if "Error Message" in data:
    raise ValueError(f"Alpha Vantage returned an error: {data['Error Message']}")

if "Information" in data:
    raise RuntimeError(f"Alpha Vantage returned information: {data['Information']}")

if "Note" in data:
    raise RuntimeError(f"Alpha Vantage returned a note: {data['Note']}")

required_keys = ["Meta Data", "Time Series (Daily)"]

missing_keys = [
    key for key in required_keys
    if key not in data
]

if missing_keys:
    raise ValueError(f"Response is missing expected keys: {missing_keys}")

time_series = data["Time Series (Daily)"]

if not time_series:
    raise ValueError("The daily time series is empty")

latest_date = next(iter(time_series))
latest_record = time_series[latest_date]

print("API response validated successfully")
print(f"Symbol: {symbol}")
print(f"Latest trading date: {latest_date}")
print(f"Latest record: {latest_record}")

extracted_at = datetime.now(timezone.utc)
timestamp = extracted_at.strftime("%Y%m%dT%H%M%SZ")

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

output_path = RAW_DATA_DIR / f"{symbol}_{timestamp}.json"

with output_path.open("w", encoding="utf-8") as file:
    json.dump(data, file, indent=2)

print(f"Raw response saved to {output_path}")