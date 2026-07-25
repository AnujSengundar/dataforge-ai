import csv
import hashlib
import json
import math
import re
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import polars as pl

from backend.app.core.config import Settings
from backend.app.models.dataset_column import DatasetColumn
from backend.app.models.profile import DatasetProfile

ENGINE_VERSION = "profiling-v1"
DATETIME_TEXT_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y/%m/%d",
    "%d-%m-%Y",
)


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
    duplicate_count = _duplicate_occurrences_after_first(dataframe)
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
        row_count=row_count,
        column_count=dataframe.width,
        duplicate_row_count=duplicate_count,
        duplicate_row_percentage=_percentage(duplicate_count, row_count),
        fully_null_row_count=fully_null_count,
        fully_null_row_percentage=_percentage(fully_null_count, row_count),
        estimated_memory_bytes=dataframe.estimated_size(),
        source_file_size_bytes=file_size_bytes,
        profiling_duration_ms=round((time.perf_counter() - started) * 1000, 3),
        profiled_at=datetime.now(UTC),
        warnings=[],
        profile_summary=_column_summary(column_records),
        engine_version=ENGINE_VERSION,
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
    unique_percentage = _percentage(distinct_count, non_null_count)
    null_percentage = _percentage(null_count, row_count)
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
    numeric_match = _match_percentage(coercion_sample, _is_numeric_text)
    datetime_match = _match_percentage(coercion_sample, _is_datetime_text)
    possible_numeric = (
        logical_type in {"string", "unknown"}
        and numeric_match >= settings.numeric_text_match_threshold
    )
    possible_datetime = (
        logical_type in {"string", "unknown"}
        and not possible_numeric
        and datetime_match >= settings.datetime_text_match_threshold
    )
    candidate_identifier = _is_candidate_identifier(
        name=name,
        logical_type=logical_type,
        non_null_count=non_null_count,
        unique_percentage=unique_percentage,
        null_percentage=null_percentage,
        settings=settings,
    )
    candidate_categorical = _is_candidate_categorical(
        logical_type=logical_type,
        non_null_count=non_null_count,
        distinct_count=distinct_count,
        unique_percentage=unique_percentage,
        is_identifier=candidate_identifier,
        settings=settings,
    )
    top_values: list[dict[str, object]] = []
    if candidate_categorical:
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
        null_percentage=null_percentage,
        distinct_count=distinct_count,
        unique_percentage=unique_percentage,
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
        is_high_null=null_percentage >= settings.high_null_threshold if row_count else False,
        is_candidate_identifier=candidate_identifier,
        is_possible_categorical=candidate_categorical,
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


def _duplicate_occurrences_after_first(dataframe: pl.DataFrame) -> int:
    if dataframe.height == 0:
        return 0
    return dataframe.height - dataframe.unique(maintain_order=False).height


def _column_summary(columns: list[DatasetColumn]) -> dict[str, int]:
    return {
        "fully_null_columns": sum(column.is_fully_null for column in columns),
        "constant_columns": sum(column.is_constant for column in columns),
        "high_null_columns": sum(column.is_high_null for column in columns),
        "candidate_identifiers": sum(column.is_candidate_identifier for column in columns),
        "candidate_categoricals": sum(column.is_possible_categorical for column in columns),
        "numeric_as_text_columns": sum(column.is_possible_numeric_text for column in columns),
        "datetime_as_text_columns": sum(column.is_possible_datetime_text for column in columns),
    }


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


def _match_percentage(values: list[str], matcher: Any) -> float:
    if not values:
        return 0.0
    matches = sum(1 for value in values if matcher(value))
    return _percentage(matches, len(values))


def _is_numeric_text(value: str) -> bool:
    numeric = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
    return numeric.fullmatch(value.strip()) is not None


def _is_datetime_text(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    for date_format in DATETIME_TEXT_FORMATS:
        try:
            datetime.strptime(candidate.replace("Z", "+0000"), date_format)
            return True
        except ValueError:
            continue
    return False


def _is_candidate_identifier(
    *,
    name: str,
    logical_type: str,
    non_null_count: int,
    unique_percentage: float,
    null_percentage: float,
    settings: Settings,
) -> bool:
    if non_null_count == 0:
        return False
    if unique_percentage < settings.identifier_unique_threshold:
        return False
    if null_percentage > settings.identifier_max_null_percentage:
        return False
    if logical_type == "decimal" and not _has_identifier_name_hint(name):
        return False
    return logical_type in {"integer", "string", "boolean", "unknown"} or _has_identifier_name_hint(
        name
    )


def _has_identifier_name_hint(name: str) -> bool:
    normalized = name.lower()
    return (
        normalized == "id"
        or normalized.endswith("_id")
        or any(hint in normalized for hint in ("code", "key"))
    )


def _is_candidate_categorical(
    *,
    logical_type: str,
    non_null_count: int,
    distinct_count: int,
    unique_percentage: float,
    is_identifier: bool,
    settings: Settings,
) -> bool:
    if is_identifier or non_null_count == 0 or distinct_count <= 1:
        return False
    if logical_type not in {"string", "integer", "boolean"}:
        return False
    return (
        unique_percentage <= settings.categorical_unique_threshold
        and distinct_count <= settings.categorical_max_distinct
    )
