from dataclasses import replace
from datetime import date
from uuid import uuid4

import polars as pl
import pytest

from backend.app.core.config import _percent, _positive_int
from backend.app.services.profiling_service import (
    _duplicate_occurrences_after_first,
    profile_dataframe,
)


def _profile(frame: pl.DataFrame, test_settings):
    return profile_dataframe(
        frame,
        dataset_version_id=uuid4(),
        file_size_bytes=123,
        settings=test_settings,
    )


def test_duplicate_row_count_after_first_occurrence(test_settings):
    frame = pl.DataFrame({"a": [1, 1, 1, 2], "b": ["x", "x", "x", "y"]})

    result = _profile(frame, test_settings)

    assert _duplicate_occurrences_after_first(frame) == 2
    assert result.profile.duplicate_row_count == 2
    assert result.profile.duplicate_row_percentage == 50.0


def test_fully_null_row_metrics(test_settings):
    frame = pl.DataFrame({"a": [None, 1, None], "b": [None, 2, None]})

    profile = _profile(frame, test_settings).profile

    assert profile.fully_null_row_count == 2
    assert profile.fully_null_row_percentage == 66.6667


def test_zero_row_profile_behavior(test_settings):
    frame = pl.DataFrame(schema={"a": pl.Int64, "b": pl.String})

    profile = _profile(frame, test_settings).profile

    assert profile.row_count == 0
    assert profile.column_count == 2
    assert profile.duplicate_row_count == 0
    assert profile.duplicate_row_percentage == 0.0
    assert profile.fully_null_row_count == 0
    assert profile.fully_null_row_percentage == 0.0


def test_estimated_memory_metric(test_settings):
    frame = pl.DataFrame({"a": [1, 2, 3]})

    profile = _profile(frame, test_settings).profile

    assert profile.estimated_memory_bytes >= 0
    assert profile.source_file_size_bytes == 123
    assert profile.profiling_duration_ms >= 0


def test_numeric_median_and_standard_deviation(test_settings):
    column = _profile(pl.DataFrame({"amount": [1.0, 2.0, 3.0]}), test_settings).columns[0]

    assert column.median_value == 2.0
    assert column.stddev_value is not None


def test_string_length_metrics(test_settings):
    column = _profile(pl.DataFrame({"name": ["a", "abcd", "xy"]}), test_settings).columns[0]

    assert column.min_length == 1
    assert column.max_length == 4
    assert column.avg_length == pytest.approx(2.3333, rel=0.001)


def test_date_range_metrics(test_settings):
    column = _profile(
        pl.DataFrame({"day": [date(2026, 1, 1), date(2026, 1, 5)]}),
        test_settings,
    ).columns[0]

    assert column.earliest_value == "2026-01-01"
    assert column.latest_value == "2026-01-05"


def test_detection_flags(test_settings):
    size = 100
    frame = pl.DataFrame(
        {
            "empty": [None] * size,
            "constant": ["x"] * size,
            "mostly_null": [None] * 50 + ["x"] * 50,
            "customer_id": [f"c{i}" for i in range(size)],
            "category": ["a"] * 98 + ["b", "c"],
            "numeric_text": [str(i) for i in range(size)],
            "datetime_text": [f"2026-01-{(i % 28) + 1:02d}" for i in range(size)],
        }
    )

    columns = {column.column_name: column for column in _profile(frame, test_settings).columns}

    assert columns["empty"].is_fully_null is True
    assert columns["empty"].is_constant is False
    assert columns["constant"].is_constant is True
    assert columns["mostly_null"].is_high_null is True
    assert columns["customer_id"].is_candidate_identifier is True
    assert columns["category"].is_possible_categorical is True
    assert columns["numeric_text"].is_possible_numeric_text is True
    assert columns["datetime_text"].is_possible_datetime_text is True


def test_threshold_boundaries(test_settings):
    settings = replace(
        test_settings,
        high_null_threshold=50.0,
        identifier_unique_threshold=100.0,
        identifier_max_null_percentage=0.0,
        categorical_unique_threshold=50.0,
        categorical_max_distinct=2,
    )
    frame = pl.DataFrame({"id": ["a", "b"], "category": ["x", "y"], "nullable": [None, "x"]})

    columns = {column.column_name: column for column in _profile(frame, settings).columns}

    assert columns["nullable"].null_percentage == 50.0
    assert columns["nullable"].is_high_null is True
    assert columns["id"].is_candidate_identifier is True
    assert columns["category"].is_possible_categorical is False


def test_invalid_configuration_values(monkeypatch):
    monkeypatch.setenv("BAD_PERCENT", "101")
    monkeypatch.setenv("BAD_INT", "0")

    with pytest.raises(ValueError):
        _percent("BAD_PERCENT", "50")
    with pytest.raises(ValueError):
        _positive_int("BAD_INT", "1")


def test_sample_limits_and_deterministic_output(test_settings):
    frame = pl.DataFrame({"value": ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]})

    first = _profile(frame, test_settings)
    second = _profile(frame, test_settings)

    assert len(first.columns[0].sample_values) == test_settings.profile_sample_values
    assert first.schema_signature == second.schema_signature
