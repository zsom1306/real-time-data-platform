from pathlib import Path

import pytest

from src.config import load_configured_symbols

def test_load_configured_symbols_normalizes_and_deduplicates(
    tmp_path: Path,
):
    config_path = tmp_path / "pipeline.toml"

    config_path.write_text(
        """
[market_data]
symbols = [" aapl ", "MSFT", "aapl", " nvda "]
""".strip(),
        encoding="utf-8",
    )

    result = load_configured_symbols(
        config_path
    )

    assert result == [
        "AAPL",
        "MSFT",
        "NVDA",
    ]

def test_load_configured_symbols_rejects_missing_file(
    tmp_path: Path,
):
    missing_path = (
        tmp_path
        / "does_not_exist.toml"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Pipeline config file was not found",
    ):
        load_configured_symbols(
            missing_path
        )

def test_load_configured_symbols_requires_market_data_section(
    tmp_path: Path,
):
    config_path = tmp_path / "pipeline.toml"

    config_path.write_text(
        """
[other_settings]
enabled = true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"\[market_data\]",
    ):
        load_configured_symbols(
            config_path
        )

@pytest.mark.parametrize(
    "config_text, expected_message",
    [
        pytest.param(
            """
[market_data]
symbols = []
""",
            "non-empty list",
            id="empty-list",
        ),
        pytest.param(
            """
[market_data]
symbols = ["AAPL", 123]
""",
            "must be a string",
            id="non-string-symbol",
        ),
        pytest.param(
            """
[market_data]
symbols = ["AAPL", "   "]
""",
            "cannot contain a blank symbol",
            id="blank-symbol",
        ),
    ],
)
def test_load_configured_symbols_rejects_invalid_symbols(
    tmp_path: Path,
    config_text: str,
    expected_message: str,
):
    config_path = tmp_path / "pipeline.toml"

    config_path.write_text(
        config_text.strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        load_configured_symbols(
            config_path
        )