import uuid
from datetime import date, datetime
from decimal import Decimal

import polars as pl

from backend.app.services.profiling_service import _serialize, infer_logical_type, profile_dataframe


def _columns(frame: pl.DataFrame, test_settings):
    result = profile_dataframe(
        frame,
        dataset_version_id=uuid.uuid4(),
        file_size_bytes=100,
        settings=test_settings,
    )
    return {column.column_name: column for column in result.columns}


def test_integer_column_metadata(test_settings):
    column = _columns(pl.DataFrame({"value": [1, 2, 3]}), test_settings)["value"]

    assert column.logical_type == "integer"
    assert column.physical_type == "Int64"
    assert column.min_value == "1.0"
    assert column.max_value == "3.0"
    assert column.mean_value == 2.0


def test_decimal_column_metadata(test_settings):
    column = _columns(pl.DataFrame({"value": [1.5, 2.5, 3.5]}), test_settings)["value"]

    assert column.logical_type == "decimal"
    assert column.min_value == "1.5"
    assert column.max_value == "3.5"
    assert column.mean_value == 2.5


def test_boolean_column_metadata(test_settings):
    column = _columns(pl.DataFrame({"flag": [True, False, True]}), test_settings)["flag"]

    assert column.logical_type == "boolean"
    assert column.distinct_count == 2


def test_string_column_metadata(test_settings):
    column = _columns(pl.DataFrame({"name": ["alpha", "beta", "gamma"]}), test_settings)["name"]

    assert column.logical_type == "string"
    assert column.min_length == 4
    assert column.max_length == 5


def test_date_column_metadata(test_settings):
    column = _columns(
        pl.DataFrame({"day": [date(2026, 1, 1), date(2026, 1, 3)]}),
        test_settings,
    )["day"]

    assert column.logical_type == "date"
    assert column.min_value == "2026-01-01"
    assert column.max_value == "2026-01-03"


def test_datetime_column_metadata(test_settings):
    column = _columns(
        pl.DataFrame({"created_at": [datetime(2026, 1, 1, 12, 0), datetime(2026, 1, 2, 12, 0)]}),
        test_settings,
    )["created_at"]

    assert column.logical_type == "datetime"
    assert column.earliest_value == "2026-01-01T12:00:00"
    assert column.latest_value == "2026-01-02T12:00:00"


def test_all_null_column_metadata(test_settings):
    column = _columns(pl.DataFrame({"empty": pl.Series([None, None])}), test_settings)["empty"]

    assert column.logical_type == "unknown"
    assert column.null_count == 2
    assert column.non_null_count == 0
    assert column.null_percentage == 100.0
    assert column.unique_percentage == 0.0
    assert column.is_fully_null is True


def test_mixed_type_column_metadata(test_settings):
    column = _columns(pl.DataFrame({"mixed": ["1", "two", "3"]}), test_settings)["mixed"]

    assert column.logical_type == "string"
    assert column.is_possible_numeric_text is False


def test_numeric_as_text_column_metadata(test_settings):
    column = _columns(pl.DataFrame({"code": ["001", "002", "003"]}), test_settings)["code"]

    assert column.logical_type == "string"
    assert column.is_possible_numeric_text is True


def test_null_percentage_definition(test_settings):
    column = _columns(pl.DataFrame({"value": [1, None, 3, None]}), test_settings)["value"]

    assert column.null_count == 2
    assert column.null_percentage == 50.0


def test_distinct_count_excludes_nulls(test_settings):
    column = _columns(pl.DataFrame({"value": [1, 1, None, 2]}), test_settings)["value"]

    assert column.distinct_count == 2


def test_unique_percentage_uses_non_null_denominator(test_settings):
    column = _columns(pl.DataFrame({"value": [1, 1, None, 2]}), test_settings)["value"]

    assert column.non_null_count == 3
    assert column.unique_percentage == 66.6667


def test_safe_min_max_for_string_column(test_settings):
    column = _columns(pl.DataFrame({"value": ["b", "a", "c"]}), test_settings)["value"]

    assert column.min_value is None
    assert column.max_value is None


def test_sample_serialization(test_settings):
    long_value = "x" * 30
    column = _columns(pl.DataFrame({"value": ["1.20", long_value, None]}), test_settings)["value"]

    assert "1.20" in column.sample_values
    assert column.sample_values[1] == "xxxxxxxxxxxxxxxxxxxx..."


def test_zero_row_behavior(test_settings):
    column = _columns(pl.DataFrame(schema={"value": pl.Int64}), test_settings)["value"]

    assert column.null_count == 0
    assert column.non_null_count == 0
    assert column.null_percentage == 0.0
    assert column.unique_percentage == 0.0


def test_normalized_logical_type_values():
    assert infer_logical_type(pl.Int64) == "integer"
    assert infer_logical_type(pl.Float64) == "decimal"
    assert infer_logical_type(pl.Boolean) == "boolean"
    assert infer_logical_type(pl.String) == "string"
    assert infer_logical_type(pl.Date) == "date"
    assert infer_logical_type(pl.Datetime) == "datetime"
    assert infer_logical_type(pl.List(pl.Int64)) == "unknown"


def test_scalar_serializer_handles_dates_decimals_and_truncation():
    assert _serialize(date(2026, 1, 1)) == "2026-01-01"
    assert _serialize(datetime(2026, 1, 1, 1, 2, 3)) == "2026-01-01T01:02:03"
    assert _serialize(Decimal("12.340")) == "12.340"
    assert _serialize("abcdefghijklmnopqrstuvwxyz", max_chars=5) == "abcde..."
