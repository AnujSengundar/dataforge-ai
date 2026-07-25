import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import Settings
from backend.app.models.comparison import DatasetVersionComparison
from backend.app.models.dataset_column import DatasetColumn
from backend.app.models.dataset_version import DatasetVersion


class ComparisonError(Exception):
    """Raised when dataset versions cannot be compared."""


def compare_versions(
    db: Session,
    *,
    dataset_id: uuid.UUID,
    settings: Settings,
    base_version_id: uuid.UUID | None = None,
    comparison_version_id: uuid.UUID | None = None,
) -> dict[str, object]:
    started = time.perf_counter()
    versions = list(
        db.scalars(
            select(DatasetVersion)
            .options(selectinload(DatasetVersion.columns), selectinload(DatasetVersion.profile))
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number.desc())
        ).all()
    )
    if base_version_id is None and comparison_version_id is None:
        if len(versions) < 2:
            raise ComparisonError("At least two dataset versions are required for comparison.")
        current, base = versions[0], versions[1]
    elif base_version_id is None or comparison_version_id is None:
        raise ComparisonError("Both base_version_id and comparison_version_id are required.")
    else:
        by_id = {version.id: version for version in versions}
        base = by_id.get(base_version_id)
        current = by_id.get(comparison_version_id)
        if base is None or current is None:
            raise ComparisonError("Both versions must belong to the selected dataset.")
    if base.id == current.id:
        raise ComparisonError("A version cannot be compared with itself.")

    previous_columns = {column.column_name: column for column in base.columns}
    current_columns = {column.column_name: column for column in current.columns}
    schema_changes = _schema_changes(base.columns, current.columns)
    column_drift = _column_drift(previous_columns, current_columns, settings)
    volume = {
        "row_count": _change(base.row_count, current.row_count),
        "column_count": _change(base.column_count, current.column_count),
        "file_size_bytes": _change(base.file_size_bytes, current.file_size_bytes),
        "duplicate_row_percentage": _change(
            base.profile.duplicate_row_percentage if base.profile else None,
            current.profile.duplicate_row_percentage if current.profile else None,
        ),
    }
    breaking = sum(item["classification"] == "breaking" for item in schema_changes)
    warnings = sum(item["status"] == "degraded" for item in column_drift)
    overall = "degraded" if breaking or warnings else "stable"
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    result: dict[str, object] = {
        "dataset_id": str(dataset_id),
        "base_version": base.version_number,
        "base_version_id": str(base.id),
        "comparison_version": current.version_number,
        "comparison_version_id": str(current.id),
        "summary": {
            "schema_changed": base.schema_signature != current.schema_signature,
            "breaking_changes": breaking,
            "warnings": warnings,
            "overall_status": overall,
        },
        "volume": volume,
        "schema_changes": schema_changes,
        "column_drift": column_drift,
        "duration_ms": duration_ms,
    }
    db.add(
        DatasetVersionComparison(
            dataset_id=dataset_id,
            base_version_id=base.id,
            comparison_version_id=current.id,
            overall_status=overall,
            result=result,
            duration_ms=duration_ms,
        )
    )
    db.commit()
    return result


def classify_schema_change(
    change_type: str,
    *,
    previous_type: str | None = None,
    current_type: str | None = None,
    nullable: bool | None = None,
) -> str:
    if change_type == "added_column":
        return "non-breaking" if nullable else "potentially_breaking"
    if change_type in {"removed_column", "nullable_to_non_nullable"}:
        return "breaking"
    if change_type == "logical_type_changed":
        if previous_type == "integer" and current_type == "decimal":
            return "non-breaking"
        return (
            "breaking" if current_type not in {previous_type, "string"} else "potentially_breaking"
        )
    if change_type == "reordered_column":
        return "potentially_breaking"
    return "potentially_breaking"


def _schema_changes(
    previous: list[DatasetColumn], current: list[DatasetColumn]
) -> list[dict[str, object]]:
    before = {column.column_name: column for column in previous}
    after = {column.column_name: column for column in current}
    changes: list[dict[str, object]] = []
    for name in sorted(after.keys() - before.keys()):
        changes.append(
            {
                "change_type": "added_column",
                "column": name,
                "classification": classify_schema_change(
                    "added_column", nullable=after[name].nullable
                ),
            }
        )
    for name in sorted(before.keys() - after.keys()):
        changes.append(
            {
                "change_type": "removed_column",
                "column": name,
                "classification": classify_schema_change("removed_column"),
            }
        )
    for name in sorted(before.keys() & after.keys()):
        old, new = before[name], after[name]
        if old.column_position != new.column_position:
            changes.append(
                {
                    "change_type": "reordered_column",
                    "column": name,
                    "previous": old.column_position,
                    "current": new.column_position,
                    "classification": classify_schema_change("reordered_column"),
                }
            )
        if old.logical_type != new.logical_type:
            changes.append(
                {
                    "change_type": "logical_type_changed",
                    "column": name,
                    "previous": old.logical_type,
                    "current": new.logical_type,
                    "classification": classify_schema_change(
                        "logical_type_changed",
                        previous_type=old.logical_type,
                        current_type=new.logical_type,
                    ),
                }
            )
        if old.nullable != new.nullable:
            change_type = (
                "nullable_to_non_nullable"
                if old.nullable and not new.nullable
                else "nullability_changed"
            )
            changes.append(
                {
                    "change_type": change_type,
                    "column": name,
                    "previous": old.nullable,
                    "current": new.nullable,
                    "classification": classify_schema_change(change_type),
                }
            )
    return changes


def _column_drift(
    previous: dict[str, DatasetColumn],
    current: dict[str, DatasetColumn],
    settings: Settings,
) -> list[dict[str, object]]:
    drift: list[dict[str, object]] = []
    for name in sorted(previous.keys() & current.keys()):
        old, new = previous[name], current[name]
        null_change = new.null_percentage - old.null_percentage
        drift.append(
            {
                "column": name,
                "metric": "null_percentage",
                "previous": old.null_percentage,
                "current": new.null_percentage,
                "change": round(null_change, 4),
                "status": "degraded"
                if null_change > settings.null_rate_drift_threshold
                else "stable",
            }
        )
        distinct_change = _relative_change(old.distinct_count, new.distinct_count)
        ratio_change = new.unique_ratio - old.unique_ratio
        drift.append(
            {
                "column": name,
                "metric": "cardinality",
                "previous_distinct_count": old.distinct_count,
                "current_distinct_count": new.distinct_count,
                "distinct_relative_change": distinct_change,
                "previous_unique_ratio": old.unique_ratio,
                "current_unique_ratio": new.unique_ratio,
                "unique_ratio_change": round(ratio_change, 6),
                "status": "degraded"
                if distinct_change is not None
                and abs(distinct_change) > settings.cardinality_drift_threshold
                else "stable",
            }
        )
        if old.logical_type in {"integer", "decimal"} and new.logical_type in {
            "integer",
            "decimal",
        }:
            for metric, old_value, new_value in (
                ("minimum", old.min_value, new.min_value),
                ("maximum", old.max_value, new.max_value),
                ("mean", old.mean_value, new.mean_value),
                ("median", old.median_value, new.median_value),
                ("standard_deviation", old.stddev_value, new.stddev_value),
            ):
                relative = _relative_change(_float(old_value), _float(new_value))
                drift.append(
                    {
                        "column": name,
                        "metric": metric,
                        "previous": _float(old_value),
                        "current": _float(new_value),
                        "relative_change": relative,
                        "status": "degraded"
                        if relative is not None and abs(relative) > settings.numeric_drift_threshold
                        else "stable",
                    }
                )
        if old.is_possible_categorical or new.is_possible_categorical:
            old_values = {str(item["value"]) for item in old.top_values}
            new_values = {str(item["value"]) for item in new.top_values}
            introduced = sorted(new_values - old_values)
            removed = sorted(old_values - new_values)
            drift.append(
                {
                    "column": name,
                    "metric": "categories",
                    "introduced_values": introduced,
                    "removed_values": removed,
                    "previous_top_values": old.top_values,
                    "current_top_values": new.top_values,
                    "status": "degraded" if introduced or removed else "stable",
                }
            )
    return drift


def _change(previous: int | float | None, current: int | float | None) -> dict[str, object]:
    if previous is None or current is None:
        return {
            "previous": previous,
            "current": current,
            "absolute_change": None,
            "percentage_change": None,
        }
    absolute = current - previous
    percentage = absolute / previous * 100 if previous else None
    return {
        "previous": previous,
        "current": current,
        "absolute_change": round(absolute, 4),
        "percentage_change": round(percentage, 4) if percentage is not None else None,
    }


def _relative_change(previous: int | float | None, current: int | float | None) -> float | None:
    if previous is None or current is None or previous == 0:
        return None
    return round((current - previous) / abs(previous), 6)


def _float(value: str | float | None) -> float | None:
    try:
        return float(value) if value is not None and value != "" else None
    except ValueError:
        return None
