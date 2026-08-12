import src.pipeline as pipeline
import pytest

def test_run_pipeline_coordinates_stages(
    monkeypatch,
):
    fake_snapshot_path = object()
    fake_raw_data = object()
    fake_clean_records = [object()]

    call_log = []

    def fake_extract_daily_data():
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

    def fake_load_daily_prices(
        clean_records,
    ):
        assert clean_records is fake_clean_records

        call_log.append(
            "load_database"
        )

        return {
            "affected_rows": 100,
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

    pipeline.run_pipeline()

    assert call_log == [
        "extract",
        "load_snapshot",
        "transform",
        "load_database",
    ]


def test_run_pipeline_rejects_empty_transformation(
    monkeypatch,
):
    fake_snapshot_path = object()
    fake_raw_data = object()

    call_log = []

    def fake_extract_daily_data():
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
        RuntimeError,
        match="The transform stage produced no clean records",
    ):
        pipeline.run_pipeline()

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
def test_run_pipeline_propagates_stage_failure(
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

    def fake_extract_daily_data():
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
        pipeline.run_pipeline()

    assert exception_info.value is expected_error

    assert call_log == expected_calls