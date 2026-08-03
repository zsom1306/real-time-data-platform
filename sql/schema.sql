CREATE SCHEMA IF NOT EXISTS market_data;

CREATE TABLE IF NOT EXISTS market_data.daily_prices (
    symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open_price NUMERIC(18, 4) NOT NULL,
    high_price NUMERIC(18, 4) NOT NULL,
    low_price NUMERIC(18, 4) NOT NULL,
    close_price NUMERIC(18, 4) NOT NULL,
    volume BIGINT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT daily_prices_primary_key
        PRIMARY KEY (symbol, trade_date),

    CONSTRAINT daily_prices_symbol_not_blank
        CHECK (BTRIM(symbol) <> ''),

    CONSTRAINT daily_prices_nonnegative_prices
        CHECK (
            open_price >= 0
            AND high_price >= 0
            AND low_price >= 0
            AND close_price >= 0
        ),

    CONSTRAINT daily_prices_valid_ohlc
        CHECK (
            high_price >= low_price
            AND high_price >= open_price
            AND high_price >= close_price
            AND low_price <= open_price
            AND low_price <= close_price
        ),

    CONSTRAINT daily_prices_nonnegative_volume
        CHECK (volume >= 0)
);