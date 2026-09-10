import logging
from time import perf_counter, sleep

from src.extract import extract_daily_data
from src.load import load_daily_prices
from src.logging_config import configure_logging
from src.transform import (load_raw_snapshot, transform_daily_records)
from src.config import load_configured_symbols
from src.s3_storage import archive_raw_snapshot

logger = logging.getLogger("src.pipeline")

def run_symbol_pipeline(
    symbol: str,
) -> dict[str, int]:
    logger.info(
        "Symbol pipeline started | symbol=%s",
        symbol,
    )

    snapshot_path = extract_daily_data(
        symbol
    )

    archive_raw_snapshot(
        snapshot_path,
        symbol,
    )

    raw_data = load_raw_snapshot(
        snapshot_path
    )

    clean_records = transform_daily_records(
        raw_data
    )

    if not clean_records:
        raise ValueError(
            "Transformation produced no clean "
            f"records for symbol {symbol}"
        )

    load_result = load_daily_prices(
        clean_records
    )

    logger.info(
        (
            "Symbol pipeline completed | "
            "symbol=%s | "
            "affected_rows=%s | "
            "rows_before_load=%s | "
            "rows_after_load=%s"
        ),
        symbol,
        load_result["affected_rows"],
        load_result["rows_before_load"],
        load_result["rows_after_load"],
    )

    return load_result

def run_pipeline() -> dict[str, dict[str, int]]:
    start_time = perf_counter()

    logger.info(
        "Daily market-data pipeline started"
    )

    try:
        symbols = load_configured_symbols()

        logger.info(
            (
                "Pipeline configuration loaded | "
                "symbols=%s"
            ),
            ",".join(symbols),
        )

        results = {}

        for index, symbol in enumerate(symbols):
            results[symbol] = (
                run_symbol_pipeline(symbol)
            )

            if index < len(symbols) - 1:
                sleep(1.2)

    except Exception:
        duration_seconds = (
            perf_counter() - start_time
        )

        logger.exception(
            (
                "Daily market-data pipeline failed | "
                "duration_seconds=%.2f"
            ),
            duration_seconds,
        )

        raise

    duration_seconds = (
        perf_counter() - start_time
    )

    logger.info(
        (
            "Daily market-data pipeline completed | "
            "symbols_processed=%s | "
            "duration_seconds=%.2f"
        ),
        len(results),
        duration_seconds,
    )

    return results

if __name__ == "__main__":
    configure_logging()
    run_pipeline()