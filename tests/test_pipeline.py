import src.pipeline as pipeline
import pytest

@pytest.fixture(autouse=True)
def disable_s3_archival(monkeypatch):
    def fake_archive_raw_snapshot(
        snapshot_path,
        symbol,
    ):
        return (
            f"s3://test-bucket/"
            f"{symbol}/snapshot.json"
        )

    monkeypatch.setattr(
        pipeline,
        "archive_raw_snapshot",
        fake_archive_raw_snapshot,
    )

def test_run_symbol_pipeline_coordinates_stages(
    monkeypatch,
):
    fake_snapshot_path = object()
    fake_raw_data = object()
    fake_clean_records = [object()]

    call_log = []

    def fake_extract_daily_data(
        symbol,
    ):
        assert symbol == "AAPL"

        call_log.append(
            "extract"
        )

        return fake_snapshot_path

    def fake_load_raw_snapshot(
        snapshot_path,
    ):
        assert snapshot_path is fake_snapshot_path

        call_log.append(
            "load_snapshot"
        )

        return fake_raw_data

    def fake_transform_daily_records(
        raw_data,
    ):
        assert raw_data is fake_raw_data

        call_log.append(
            "transform"
        )

        return fake_clean_records

    expected_result = {
        "affected_rows": 100,
        "rows_before_load": 100,
        "rows_after_load": 101,
    }

    def fake_load_daily_prices(
        clean_records,
    ):
        assert clean_records is fake_clean_records

        call_log.append(
            "load_database"
        )

        return expected_result

    monkeypatch.setattr(
        pipeline,
        "extract_daily_data",
        fake_extract_daily_data,
    )

    monkeypatch.setattr(
        pipeline,
        "load_raw_snapshot",
        fake_load_raw_snapshot,
    )

    monkeypatch.setattr(
        pipeline,
        "transform_daily_records",
        fake_transform_daily_records,
    )

    monkeypatch.setattr(
        pipeline,
        "load_daily_prices",
        fake_load_daily_prices,
    )

    result = pipeline.run_symbol_pipeline(
        "AAPL"
    )

    assert result is expected_result

    assert call_log == [
        "extract",
        "load_snapshot",
        "transform",
        "load_database",
    ]


def test_run_symbol_pipeline_rejects_empty_transformation(
    monkeypatch,
):
    fake_snapshot_path = object()
    fake_raw_data = object()

    call_log = []

    def fake_extract_daily_data(
        symbol,
    ):
        assert symbol == "AAPL"

        call_log.append(
            "extract"
        )

        return fake_snapshot_path

    def fake_load_raw_snapshot(
        snapshot_path,
    ):
        assert snapshot_path is fake_snapshot_path

        call_log.append(
            "load_snapshot"
        )

        return fake_raw_data

    def fake_transform_daily_records(
        raw_data,
    ):
        assert raw_data is fake_raw_data

        call_log.append(
            "transform"
        )

        return []

    def fake_load_daily_prices(
        clean_records,
    ):
        pytest.fail(
            "Database loading should not occur "
            "when transformation returns no records"
        )

    monkeypatch.setattr(
        pipeline,
        "extract_daily_data",
        fake_extract_daily_data,
    )

    monkeypatch.setattr(
        pipeline,
        "load_raw_snapshot",
        fake_load_raw_snapshot,
    )

    monkeypatch.setattr(
        pipeline,
        "transform_daily_records",
        fake_transform_daily_records,
    )

    monkeypatch.setattr(
        pipeline,
        "load_daily_prices",
        fake_load_daily_prices,
    )

    with pytest.raises(
        ValueError,
        match="Transformation produced no clean records",
    ):
        pipeline.run_symbol_pipeline(
            "AAPL"
        )

    assert call_log == [
        "extract",
        "load_snapshot",
        "transform",
    ]


@pytest.mark.parametrize(
    "failing_stage, expected_calls",
    [
        pytest.param(
            "extract",
            ["extract"],
            id="extract-failure",
        ),
        pytest.param(
            "load_snapshot",
            [
                "extract",
                "load_snapshot",
            ],
            id="snapshot-failure",
        ),
        pytest.param(
            "transform",
            [
                "extract",
                "load_snapshot",
                "transform",
            ],
            id="transform-failure",
        ),
        pytest.param(
            "load_database",
            [
                "extract",
                "load_snapshot",
                "transform",
                "load_database",
            ],
            id="database-failure",
        ),
    ],
)
def test_run_symbol_pipeline_propagates_stage_failure(
    monkeypatch,
    failing_stage,
    expected_calls,
):
    fake_snapshot_path = object()
    fake_raw_data = object()
    fake_clean_records = [object()]

    call_log = []

    expected_error = RuntimeError(
        f"{failing_stage} failed"
    )

    def fake_extract_daily_data(
        symbol,
    ):
        assert symbol == "AAPL"

        call_log.append(
            "extract"
        )

        if failing_stage == "extract":
            raise expected_error

        return fake_snapshot_path

    def fake_load_raw_snapshot(
        snapshot_path,
    ):
        assert snapshot_path is fake_snapshot_path

        call_log.append(
            "load_snapshot"
        )

        if failing_stage == "load_snapshot":
            raise expected_error

        return fake_raw_data

    def fake_transform_daily_records(
        raw_data,
    ):
        assert raw_data is fake_raw_data

        call_log.append(
            "transform"
        )

        if failing_stage == "transform":
            raise expected_error

        return fake_clean_records

    def fake_load_daily_prices(
        clean_records,
    ):
        assert clean_records is fake_clean_records

        call_log.append(
            "load_database"
        )

        if failing_stage == "load_database":
            raise expected_error

        return {
            "affected_rows": 1,
            "rows_before_load": 100,
            "rows_after_load": 101,
        }

    monkeypatch.setattr(
        pipeline,
        "extract_daily_data",
        fake_extract_daily_data,
    )

    monkeypatch.setattr(
        pipeline,
        "load_raw_snapshot",
        fake_load_raw_snapshot,
    )

    monkeypatch.setattr(
        pipeline,
        "transform_daily_records",
        fake_transform_daily_records,
    )

    monkeypatch.setattr(
        pipeline,
        "load_daily_prices",
        fake_load_daily_prices,
    )

    with pytest.raises(
        RuntimeError
    ) as exception_info:
        pipeline.run_symbol_pipeline(
            "AAPL"
        )

    assert exception_info.value is expected_error

    assert call_log == expected_calls


def test_run_pipeline_processes_configured_symbols(
    monkeypatch,
):
    configured_symbols = [
        "AAPL",
        "MSFT",
        "NVDA",
    ]

    call_log = []

    def fake_load_configured_symbols():
        call_log.append(
            "load_config"
        )

        return configured_symbols

    def fake_run_symbol_pipeline(
        symbol,
    ):
        call_log.append(
            symbol
        )

        return {
            "affected_rows": 1,
            "rows_before_load": 0,
            "rows_after_load": 1,
        }

    monkeypatch.setattr(
        pipeline,
        "load_configured_symbols",
        fake_load_configured_symbols,
    )

    monkeypatch.setattr(
        pipeline,
        "run_symbol_pipeline",
        fake_run_symbol_pipeline,
    )

    result = pipeline.run_pipeline()

    assert call_log == [
        "load_config",
        "AAPL",
        "MSFT",
        "NVDA",
    ]

    assert set(result) == {
        "AAPL",
        "MSFT",
        "NVDA",
    }


def test_run_pipeline_stops_after_symbol_failure(
    monkeypatch,
):
    configured_symbols = [
        "AAPL",
        "MSFT",
        "NVDA",
    ]

    call_log = []

    expected_error = RuntimeError(
        "MSFT pipeline failed"
    )

    def fake_load_configured_symbols():
        return configured_symbols

    def fake_run_symbol_pipeline(
        symbol,
    ):
        call_log.append(
            symbol
        )

        if symbol == "MSFT":
            raise expected_error

        if symbol == "NVDA":
            pytest.fail(
                "NVDA should not run after "
                "MSFT fails"
            )

        return {
            "affected_rows": 1,
            "rows_before_load": 0,
            "rows_after_load": 1,
        }

    monkeypatch.setattr(
        pipeline,
        "load_configured_symbols",
        fake_load_configured_symbols,
    )

    monkeypatch.setattr(
        pipeline,
        "run_symbol_pipeline",
        fake_run_symbol_pipeline,
    )

    with pytest.raises(
        RuntimeError
    ) as exception_info:
        pipeline.run_pipeline()

    assert exception_info.value is expected_error

    assert call_log == [
        "AAPL",
        "MSFT",
    ]