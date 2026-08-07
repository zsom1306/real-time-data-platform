import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import gmtime

LOG_DIRECTORY = Path("logs")
LOG_FILE = LOG_DIRECTORY / "pipeline.log"

def configure_logging() -> None:
    """Configure console and rotating-file logging for the project."""

    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    log_formatter = logging.Formatter(
        fmt=(
            "%(asctime)sZ | "
            "%(levelname)-8s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    log_formatter.converter = gmtime

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8"
    )

    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    root_logger.handlers.clear()

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    project_logger = logging.getLogger("src")
    project_logger.setLevel(logging.DEBUG)