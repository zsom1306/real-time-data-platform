from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CONFIG_PATH = (
    PROJECT_ROOT
    / "config"
    / "pipeline.toml"
)


def load_configured_symbols(
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> list[str]:
    if not config_path.exists():
        raise FileNotFoundError(
            f"Pipeline config file was not found: "
            f"{config_path}"
        )

    if not config_path.is_file():
        raise ValueError(
            f"Pipeline config path is not a file: "
            f"{config_path}"
        )

    try:
        with config_path.open("rb") as config_file:
            config = tomllib.load(config_file)

    except tomllib.TOMLDecodeError as error:
        raise ValueError(
            f"Pipeline config is not valid TOML: "
            f"{config_path}"
        ) from error

    market_data_config = config.get(
        "market_data"
    )

    if not isinstance(
        market_data_config,
        dict,
    ):
        raise ValueError(
            "Pipeline config must contain "
            "a [market_data] section"
        )

    raw_symbols = market_data_config.get(
        "symbols"
    )

    if (
        not isinstance(raw_symbols, list)
        or not raw_symbols
    ):
        raise ValueError(
            "market_data.symbols must be "
            "a non-empty list"
        )

    configured_symbols = []
    seen_symbols = set()

    for raw_symbol in raw_symbols:
        if not isinstance(raw_symbol, str):
            raise ValueError(
                "Every market_data.symbols "
                "value must be a string"
            )

        symbol = raw_symbol.strip().upper()

        if not symbol:
            raise ValueError(
                "market_data.symbols cannot "
                "contain a blank symbol"
            )

        if symbol not in seen_symbols:
            configured_symbols.append(
                symbol
            )

            seen_symbols.add(
                symbol
            )

    return configured_symbols