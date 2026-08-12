import json
from pathlib import Path

import pytest

import src.extract as extract

def test_extract_daily_data_saves_valid_snapshot(
    tmp_path: Path,
    monkeypatch,
):
    fake_api_response = {
        "Meta Data": {
            "2. Symbol": "AAPL",
        },
        "Time Series (Daily)": {
            "2026-08-11": {
                "1. open": "220.0000",
                "2. high": "225.0000",
                "3. low": "218.0000",
                "4. close": "223.0000",
                "5. volume": "1500000",
            },
        },
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return fake_api_response

    def fake_get(url, params, timeout):
        assert url == extract.BASE_URL
        assert params["function"] == "TIME_SERIES_DAILY"
        assert params["symbol"] == "AAPL"
        assert params["outputsize"] == "compact"
        assert params["datatype"] == "json"
        assert params["apikey"] == "fake-test-api-key"
        assert timeout == 30

        return FakeResponse()

    monkeypatch.setenv(
        "ALPHA_VANTAGE_API_KEY",
        "fake-test-api-key",
    )

    monkeypatch.setattr(
        extract.requests,
        "get",
        fake_get,
    )

    monkeypatch.setattr(
        extract,
        "RAW_DATA_DIR",
        tmp_path,
    )

    snapshot_path = extract.extract_daily_data(
        " aapl "
    )

    assert snapshot_path.exists()
    assert snapshot_path.parent == tmp_path
    assert snapshot_path.name.startswith("AAPL_")
    assert snapshot_path.suffix == ".json"

    with snapshot_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        saved_data = json.load(file)

    assert saved_data == fake_api_response


def test_extract_daily_data_rejects_blank_symbol(
    monkeypatch,
):
    def fail_if_called(*args, **kwargs):
        pytest.fail(
            "requests.get should not be called for a blank symbol"
        )

    monkeypatch.setattr(
        extract.requests,
        "get",
        fail_if_called,
    )

    with pytest.raises(
        ValueError,
        match="The stock symbol cannot be blank",
    ):
        extract.extract_daily_data("   ")


def test_extract_daily_data_rejects_missing_api_key(
    monkeypatch,
):
    monkeypatch.delenv(
        "ALPHA_VANTAGE_API_KEY",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="ALPHA_VANTAGE_API_KEY was not found or is blank",
    ):
        extract.extract_daily_data("AAPL")


@pytest.mark.parametrize(
    "fake_api_response, expected_exception, expected_message",
    [
        pytest.param(
            {
                "Error Message": "Invalid API call."
            },
            ValueError,
            "Alpha Vantage returned an error",
            id="error-message",
        ),
        pytest.param(
            {
                "Information": "API usage information."
            },
            RuntimeError,
            "Alpha Vantage returned information",
            id="information",
        ),
        pytest.param(
            {
                "Note": "API rate limit reached."
            },
            RuntimeError,
            "Alpha Vantage returned a note",
            id="note",
        ),
    ],
)
def test_extract_daily_data_rejects_alpha_vantage_error_response(
    tmp_path: Path,
    monkeypatch,
    fake_api_response,
    expected_exception,
    expected_message: str,
):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return fake_api_response

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setenv(
        "ALPHA_VANTAGE_API_KEY",
        "fake-test-api-key",
    )

    monkeypatch.setattr(
        extract.requests,
        "get",
        fake_get,
    )

    monkeypatch.setattr(
        extract,
        "RAW_DATA_DIR",
        tmp_path,
    )

    with pytest.raises(
        expected_exception,
        match=expected_message,
    ):
        extract.extract_daily_data("AAPL")

    assert list(tmp_path.iterdir()) == []


def test_extract_daily_data_rejects_missing_required_keys(
    tmp_path: Path,
    monkeypatch,
):
    fake_api_response = {
        "Meta Data": {
            "2. Symbol": "AAPL",
        },
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return fake_api_response

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setenv(
        "ALPHA_VANTAGE_API_KEY",
        "fake-test-api-key",
    )

    monkeypatch.setattr(
        extract.requests,
        "get",
        fake_get,
    )

    monkeypatch.setattr(
        extract,
        "RAW_DATA_DIR",
        tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="Response is missing expected keys",
    ):
        extract.extract_daily_data("AAPL")

    assert list(tmp_path.iterdir()) == []


def test_extract_daily_data_rejects_empty_time_series(
    tmp_path: Path,
    monkeypatch,
):
    fake_api_response = {
        "Meta Data": {
            "2. Symbol": "AAPL",
        },
        "Time Series (Daily)": {},
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return fake_api_response

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setenv(
        "ALPHA_VANTAGE_API_KEY",
        "fake-test-api-key",
    )

    monkeypatch.setattr(
        extract.requests,
        "get",
        fake_get,
    )

    monkeypatch.setattr(
        extract,
        "RAW_DATA_DIR",
        tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="The daily time series is empty",
    ):
        extract.extract_daily_data("AAPL")

    assert list(tmp_path.iterdir()) == []


def test_extract_daily_data_propagates_http_error(
    monkeypatch,
):
    class FakeResponse:
        def raise_for_status(self):
            raise extract.requests.HTTPError(
                "500 Server Error"
            )

        def json(self):
            pytest.fail(
                "response.json() should not be called "
                "after an HTTP error"
            )

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setenv(
        "ALPHA_VANTAGE_API_KEY",
        "fake-test-api-key",
    )

    monkeypatch.setattr(
        extract.requests,
        "get",
        fake_get,
    )

    with pytest.raises(
        extract.requests.HTTPError,
        match="500 Server Error",
    ):
        extract.extract_daily_data("AAPL")


def test_extract_daily_data_rejects_non_object_json(
    tmp_path: Path,
    monkeypatch,
):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return []

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setenv(
        "ALPHA_VANTAGE_API_KEY",
        "fake-test-api-key",
    )

    monkeypatch.setattr(
        extract.requests,
        "get",
        fake_get,
    )

    monkeypatch.setattr(
        extract,
        "RAW_DATA_DIR",
        tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="Expected the Alpha Vantage response to be a JSON object",
    ):
        extract.extract_daily_data("AAPL")

    assert list(tmp_path.iterdir()) == []