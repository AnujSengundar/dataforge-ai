import csv
import hashlib
import json
import math
import re
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import polars as pl

from backend.app.core.config import Settings
from backend.app.models.dataset_column import DatasetColumn
from backend.app.models.profile import DatasetProfile


class TabularDataError(Exception):
    """Raised when source data is not a valid supported table."""


@dataclass(frozen=True)
class ProfileResult:
    dataframe: pl.DataFrame
    profile: DatasetProfile
    columns: list[DatasetColumn]
    schema_signature: str


def read_tabular(path: Path, file_format: str) -> pl.DataFrame:
    try:
        if file_format == "csv":
            _validate_csv_header(path)
            frame = pl.read_csv(path, try_parse_dates=True, infer_schema_length=10_000)
        elif file_format == "parquet":
            if path.read_bytes()[:4] != b"PAR1":
                raise TabularDataError("File content is not a valid Parquet file.")
            frame = pl.read_parquet(path)
        else:
            raise TabularDataError(f"Unsupported tabular format: {file_format}.")
    except TabularDataError:
        raise
    except Exception as exc:
        raise TabularDataError("Unable to parse the uploaded tabular file.") from exc
    if not frame.columns:
        raise TabularDataError("Uploaded table has no columns.")
    if len(frame.columns) != len(set(frame.columns)):
        raise TabularDataError("Uploaded table has duplicate column names.")
    return frame


def profile_dataframe(
    dataframe: pl.DataFrame,
    *,
    dataset_version_id: uuid.UUID,
    file_size_bytes: int,
    settings: Settings,
) -> ProfileResult:
    started = time.perf_counter()
    row_count = dataframe.height
    column_records = [
        _profile_column(dataset_version_id, name, position, dataframe[name], row_count, settings)
        for position, name in enumerate(dataframe.columns)
    ]
    definitions = [
        {
            "column_name": column.column_name,
            "logical_type": column.logical_type,
            "nullable": column.nullable,
            "ordinal_position": column.column_position,
        }
        for column in column_records
    ]
    signature = hashlib.sha256(
        json.dumps(definitions, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    duplicate_count = int(dataframe.is_duplicated().sum()) if row_count else 0
    fully_null_count = (
        int(
            dataframe.select(
                pl.all_horizontal([pl.col(name).is_null() for name in dataframe.columns]).sum()
            ).item()
        )
        if row_count
        else 0
    )
    profile = DatasetProfile(
        dataset_version_id=dataset_version_id,
        total_rows=row_count,
        total_columns=dataframe.width,
        duplicate_row_count=duplicate_count,
        duplicate_row_percentage=_percentage(duplicate_count, row_count),
        fully_null_row_count=fully_null_count,
        estimated_memory_bytes=dataframe.estimated_size(),
        file_size_bytes=file_size_bytes,
        execution_duration_ms=round((time.perf_counter() - started) * 1000, 3),
    )
    return ProfileResult(dataframe, profile, column_records, signature)


def _validate_csv_header(path: Path) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            header = next(csv.reader(source), None)
    except UnicodeDecodeError as exc:
        raise TabularDataError("CSV must use UTF-8 compatible text encoding.") from exc
    if not header or all(not name.strip() for name in header):
        raise TabularDataError("CSV has no columns.")
    normalized = [name.strip() for name in header]
    if any(not name for name in normalized):
        raise TabularDataError("CSV contains an empty column name.")
    if len(normalized) != len(set(normalized)):
        raise TabularDataError("CSV contains duplicate column names.")


def _profile_column(
    version_id: uuid.UUID,
    name: str,
    position: int,
    series: pl.Series,
    row_count: int,
    settings: Settings,
) -> DatasetColumn:
    null_count = series.null_count()
    non_null = series.drop_nulls()
    non_null_count = len(non_null)
    distinct_count = int(non_null.n_unique()) if non_null_count else 0
    unique_ratio = distinct_count / non_null_count if non_null_count else 0.0
    logical_type = infer_logical_type(series.dtype)
    minimum: str | None = None
    maximum: str | None = None
    mean: float | None = None
    median: float | None = None
    stddev: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    avg_length: float | None = None
    earliest: str | None = None
    latest: str | None = None

    if non_null_count and logical_type in {"integer", "decimal"}:
        numeric = non_null.cast(pl.Float64)
        minimum = _serialize(numeric.min())
        maximum = _serialize(numeric.max())
        mean = _finite(numeric.mean())
        median = _finite(numeric.median())
        stddev = _finite(numeric.std())
    elif non_null_count and logical_type in {"date", "datetime"}:
        earliest = _serialize(non_null.min())
        latest = _serialize(non_null.max())
        minimum, maximum = earliest, latest
    elif non_null_count:
        lengths = non_null.cast(pl.String).str.len_chars()
        min_length = int(lengths.min())
        max_length = int(lengths.max())
        avg_length = _finite(lengths.mean())

    sample = non_null.unique(maintain_order=True).head(settings.profile_sample_values).to_list()
    coercion_sample = non_null.head(settings.type_coercion_sample_size).cast(pl.String).to_list()
    possible_numeric = logical_type == "string" and _all_numeric(coercion_sample)
    possible_datetime = logical_type == "string" and _all_datetime(coercion_sample)
    top_values: list[dict[str, object]] = []
    if unique_ratio <= settings.categorical_unique_ratio_threshold:
        for item in non_null.value_counts(sort=True).head(settings.category_value_limit).to_dicts():
            value = item.get(name)
            count = item.get("count", 0)
            top_values.append({"value": _serialize(value), "count": int(count)})

    return DatasetColumn(
        dataset_version_id=version_id,
        column_name=name,
        column_position=position,
        logical_type=logical_type,
        physical_type=str(series.dtype),
        nullable=null_count > 0,
        null_count=null_count,
        non_null_count=non_null_count,
        null_percentage=_percentage(null_count, row_count),
        distinct_count=distinct_count,
        unique_percentage=_percentage(distinct_count, non_null_count),
        sample_values=[
            _serialize(value, max_chars=settings.profile_sample_max_chars) for value in sample
        ],
        min_value=minimum,
        max_value=maximum,
        mean_value=mean,
        median_value=median,
        stddev_value=stddev,
        min_length=min_length,
        max_length=max_length,
        avg_length=avg_length,
        earliest_value=earliest,
        latest_value=latest,
        is_constant=non_null_count > 0 and distinct_count == 1,
        is_fully_null=non_null_count == 0,
        is_high_null=(null_count / row_count) >= settings.high_null_threshold
        if row_count
        else False,
        is_candidate_identifier=(
            non_null_count > 0
            and unique_ratio >= settings.identifier_unique_ratio_threshold
            and null_count == 0
        ),
        is_possible_categorical=(
            non_null_count > 0 and unique_ratio <= settings.categorical_unique_ratio_threshold
        ),
        is_possible_datetime_text=possible_datetime,
        is_possible_numeric_text=possible_numeric,
        top_values=top_values,
    )


def infer_logical_type(dtype: pl.DataType) -> str:
    if dtype.is_integer():
        return "integer"
    if dtype.is_float() or dtype.is_decimal():
        return "decimal"
    if dtype == pl.Boolean:
        return "boolean"
    if dtype == pl.Date:
        return "date"
    if dtype == pl.Datetime or isinstance(dtype, pl.Datetime):
        return "datetime"
    if dtype in {pl.String, pl.Categorical, pl.Enum}:
        return "string"
    return "unknown"


def _percentage(part: int, total: int) -> float:
    return round(part / total * 100, 4) if total else 0.0


def _serialize(value: Any, *, max_chars: int = 200) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        result = format(value, "f")
    elif isinstance(value, (date, datetime)):
        result = value.isoformat()
    elif hasattr(value, "item"):
        try:
            return _serialize(value.item(), max_chars=max_chars)
        except (AttributeError, TypeError, ValueError):
            result = str(value)
    else:
        result = str(value)
    if len(result) > max_chars:
        return f"{result[:max_chars]}..."
    return result


def _finite(value: float | int | None) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    return float(value)


def _all_numeric(values: list[str]) -> bool:
    if not values:
        return False
    numeric = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
    return all(numeric.fullmatch(value.strip()) is not None for value in values)


def _all_datetime(values: list[str]) -> bool:
    if not values:
        return False
    try:
        for value in values:
            datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True
