import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
from dotenv import load_dotenv


logger = logging.getLogger("src.s3_storage")

load_dotenv()

SNAPSHOT_TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"


def get_required_s3_setting(
    name: str,
) -> str:
    """Return a required S3-related environment setting."""

    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value.strip()


def create_s3_client():
    """Create an authenticated Amazon S3 client."""

    region = get_required_s3_setting(
        "AWS_REGION"
    )

    profile_name = os.getenv(
        "AWS_PROFILE"
    )

    if (
        profile_name is not None
        and profile_name.strip()
    ):
        session = boto3.Session(
            profile_name=profile_name.strip(),
            region_name=region,
        )
    else:
        session = boto3.Session(
            region_name=region,
        )

    return session.client("s3")


def build_raw_snapshot_key(
    snapshot_path: Path,
    symbol: str,
) -> str:
    """Build the partitioned S3 key for a raw snapshot."""

    normalized_symbol = (
        symbol.strip().upper()
    )

    if not normalized_symbol:
        raise ValueError(
            "The stock symbol cannot be blank"
        )

    if not snapshot_path.exists():
        raise FileNotFoundError(
            f"Raw snapshot was not found: "
            f"{snapshot_path}"
        )

    if not snapshot_path.is_file():
        raise ValueError(
            f"Expected a snapshot file: "
            f"{snapshot_path}"
        )

    if not snapshot_path.name.startswith(
        f"{normalized_symbol}_"
    ):
        raise ValueError(
            "Snapshot filename does not match "
            f"symbol {normalized_symbol}: "
            f"{snapshot_path.name}"
        )

    timestamp_text = (
        snapshot_path.stem.rsplit(
            "_",
            maxsplit=1,
        )[-1]
    )

    try:
        extracted_at = datetime.strptime(
            timestamp_text,
            SNAPSHOT_TIMESTAMP_FORMAT,
        ).replace(
            tzinfo=timezone.utc
        )

    except ValueError as error:
        raise ValueError(
            "Snapshot filename does not contain "
            "the expected UTC timestamp: "
            f"{snapshot_path.name}"
        ) from error

    return (
        "raw/"
        "alpha_vantage/"
        "daily/"
        f"symbol={normalized_symbol}/"
        f"year={extracted_at:%Y}/"
        f"month={extracted_at:%m}/"
        f"day={extracted_at:%d}/"
        f"{snapshot_path.name}"
    )


def archive_raw_snapshot(
    snapshot_path: Path,
    symbol: str,
) -> str:
    """Upload a raw JSON snapshot to Amazon S3."""

    bucket_name = get_required_s3_setting(
        "S3_RAW_BUCKET"
    )

    object_key = build_raw_snapshot_key(
        snapshot_path,
        symbol,
    )

    s3_client = create_s3_client()

    s3_client.upload_file(
        str(snapshot_path),
        bucket_name,
        object_key,
        ExtraArgs={
            "ContentType": "application/json",
        },
    )

    s3_uri = (
        f"s3://{bucket_name}/{object_key}"
    )

    logger.info(
        (
            "Raw snapshot archived to S3 | "
            "symbol=%s | s3_uri=%s"
        ),
        symbol.strip().upper(),
        s3_uri,
    )

    return s3_uri