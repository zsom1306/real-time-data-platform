import logging
from time import perf_counter

from src.extract import extract_daily_data
from src.load import load_daily_prices
from src.logging_config import configure_logging
from src.transform import (load_raw_snapshot, transform_daily_records)

logger = logging.getLogger("src.pipeline")


def run_pipeline() -> None:
    """Run the complete daily market-data ETL pipeline."""

    pipeline_start_time = perf_counter()

    logger.info("Daily market-data pipeline started")

    try:
        logger.debug("Stage 1/3 started | stage=extract")

        snapshot_path = extract_daily_data()

        logger.debug(
            "Stage 1/3 completed | "
            "stage=extract | snapshot_path=%s",
            snapshot_path,
        )

        logger.debug("Stage 2/3 started | stage=transform")

        raw_data = load_raw_snapshot(snapshot_path)

        clean_records = transform_daily_records(raw_data)

        if not clean_records:
            raise RuntimeError(
                "The transform stage produced no clean records"
            )

        logger.debug(
            "Stage 2/3 completed | "
            "stage=transform | clean_records=%d",
            len(clean_records),
        )

        logger.debug("Stage 3/3 started | stage=load")

        load_result = load_daily_prices(clean_records)

        logger.debug(
            "Stage 3/3 completed | "
            "stage=load | affected_rows=%d | "
            "rows_before=%d | rows_after=%d",
            load_result["affected_rows"],
            load_result["rows_before_load"],
            load_result["rows_after_load"],
        )

    except Exception:
        pipeline_duration = (
            perf_counter() - pipeline_start_time
        )

        logger.exception(
            "Daily market-data pipeline failed | "
            "duration_seconds=%.2f",
            pipeline_duration,
        )

        raise

    pipeline_duration = perf_counter() - pipeline_start_time

    logger.info(
        "Daily market-data pipeline completed successfully | "
        "snapshot_path=%s | "
        "affected_rows=%d | "
        "rows_before=%d | "
        "rows_after=%d | "
        "duration_seconds=%.2f",
        snapshot_path,
        load_result["affected_rows"],
        load_result["rows_before_load"],
        load_result["rows_after_load"],
        pipeline_duration,
    )

if __name__ == "__main__":
    configure_logging()
    run_pipeline()