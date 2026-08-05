from time import perf_counter

from src.extract import extract_daily_data
from src.load import load_daily_prices
from src.transform import (load_raw_snapshot, transform_daily_records)


def run_pipeline() -> None:
    """Run the complete daily market-data ETL pipeline."""

    pipeline_start_time = perf_counter()

    print("Starting daily market-data pipeline.")

    print("\n[1/3] Extracting daily market data...")
    snapshot_path = extract_daily_data()

    print("\n[2/3] Transforming raw market data...")
    raw_data = load_raw_snapshot(snapshot_path)
    clean_records = transform_daily_records(raw_data)

    if not clean_records:
        raise RuntimeError("The transform stage produced no clean records")

    print(f"Clean records prepared: {len(clean_records)}")

    print("\n[3/3] Loading records into PostgreSQL...")
    load_result = load_daily_prices(clean_records)

    pipeline_duration = perf_counter() - pipeline_start_time

    print("\nPipeline completed successfully.")
    print(f"Raw snapshot: {snapshot_path}")
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
    print(
        f"Pipeline duration: {pipeline_duration:.2f} seconds"
    )

if __name__ == "__main__":
    run_pipeline()