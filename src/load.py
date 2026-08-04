import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_required_environment_variable(name: str) -> str:
    """Return a required environment variable or raise a clear error."""

    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def create_database_connection() -> psycopg.Connection:
    """Create and return a connection to the PostgreSQL database."""

    return psycopg.connect(
        host=get_required_environment_variable("DB_HOST"),
        port=int(get_required_environment_variable("DB_PORT")),
        dbname=get_required_environment_variable("DB_NAME"),
        user=get_required_environment_variable("DB_USER"),
        password=get_required_environment_variable("DB_PASSWORD"),
        connect_timeout=10,
    )

def verify_database_connection() -> None:
    """Connect to PostgreSQL and verify the expected database and table."""

    with create_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user;")

            connection_result = cursor.fetchone()

            if connection_result is None:
                raise RuntimeError("PostgreSQL returned no connection information.")
            
            database_name, database_user = connection_result

            cursor.execute("SELECT COUNT(*) FROM market_data.daily_prices")

            count_result = cursor.fetchone()

            if count_result is None:
                raise RuntimeError("PostgreSQL returned no table row count.")

            daily_price_count = count_result[0]

    print("Database connection successful.")
    print(f"Connected database: {database_name}")
    print(f"Connected user: {database_user}")
    print(f"daily_prices row count: {daily_price_count}")

if __name__ == "__main__":
    verify_database_connection()
