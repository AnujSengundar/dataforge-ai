import logging
import math
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime

import polars as pl
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.models.data_contract import DataContract
from backend.app.models.dataset_version import DatasetVersion
from backend.app.models.validation import QuarantinedRow, ValidationResult, ValidationRun
from backend.app.rules import ValidationContext, evaluate_rule
from backend.app.rules.base import RuleEvaluation
from backend.app.schemas.contract import ContractRules
from backend.app.services.contract_service import get_active_contract
from backend.app.services.profiling_service import read_tabular
from backend.app.services.quality_score_service import calculate_quality_score
from backend.app.services.storage_service import LocalStorage


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation cannot be executed."""


def run_validation(
    db: Session,
    *,
    dataset_id: uuid.UUID,
    version_id: uuid.UUID,
    settings: Settings,
) -> ValidationRun:
    version = db.scalar(
        select(DatasetVersion).where(
            DatasetVersion.id == version_id, DatasetVersion.dataset_id == dataset_id
        )
    )
    if version is None:
        raise ValidationError("Dataset version not found.")
    contract = get_active_contract(db, dataset_id)
    run = ValidationRun(
        dataset_id=dataset_id,
        dataset_version_id=version_id,
        contract_id=contract.id if contract else None,
        contract_version=contract.version if contract else None,
        status="running",
        started_at=datetime.now(UTC),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    started = time.perf_counter()
    storage = LocalStorage(settings.upload_dir)
    try:
        frame = read_tabular(storage.resolve(version.storage_path), version.file_format)
        if any(name.startswith("_dataforge_") for name in frame.columns):
            raise ValidationError("Source columns using the reserved '_dataforge_' prefix are not supported.")
        evaluations = _evaluate_contract(frame, version, contract)
        failure_map: dict[int, list[tuple[str, str]]] = {}
        results: list[ValidationResult] = []
        for code, column, evaluation in evaluations:
            for index in evaluation.invalid_row_indexes:
                failure_map.setdefault(index, []).append((code, evaluation.message))
            results.append(_result_model(run.id, code, column, evaluation))

        indexed = frame.with_row_index("_dataforge_source_row_number", offset=1)
        invalid_indexes = sorted(failure_map)
        invalid_mask = pl.Series(
            "_invalid", [index in failure_map for index in range(frame.height)], dtype=pl.Boolean
        )
        metadata = [
            pl.lit(str(version_id)).alias("_dataforge_dataset_version_id"),
            pl.lit(str(run.id)).alias("_dataforge_validation_run_id"),
        ]
        accepted = indexed.filter(~invalid_mask).with_columns(metadata)
        quarantined = indexed.filter(invalid_mask).with_columns(
            metadata
            + [
                pl.Series(
                    "_dataforge_failed_rule_codes",
                    [[code for code, _ in failure_map[index]] for index in invalid_indexes],
                ),
                pl.Series(
                    "_dataforge_failure_messages",
                    [[message for _, message in failure_map[index]] for index in invalid_indexes],
                ),
                pl.lit(datetime.now(UTC)).alias("_dataforge_quarantine_timestamp"),
            ]
        )
        accepted_key, accepted_path = storage.validation_path(
            dataset_id, version_id, run.id, "accepted.parquet"
        )
        quarantine_key, quarantine_path = storage.validation_path(
            dataset_id, version_id, run.id, "quarantine.parquet"
        )
        accepted.write_parquet(accepted_path)
        quarantined.write_parquet(quarantine_path)

        passed = sum(item.status == "passed" for _, _, item in evaluations)
        failed = sum(item.status == "failed" for _, _, item in evaluations)
        blocking = sum(item.status != "skipped" for _, _, item in evaluations)
        score = calculate_quality_score(
            total_rows=frame.height,
            valid_rows=frame.height - len(invalid_indexes),
            passed_blocking_rules=passed,
            total_blocking_rules=blocking,
            row_weight=settings.quality_row_weight,
            rule_weight=settings.quality_rule_weight,
        )
        db.add_all(results)
        for batch in _quarantine_batches(
            frame, invalid_indexes, failure_map, run.id, version_id, batch_size=1000
        ):
            db.add_all(batch)
            db.flush()
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        run.total_rows = frame.height
        run.valid_rows = frame.height - len(invalid_indexes)
        run.invalid_rows = len(invalid_indexes)
        run.passed_rules = passed
        run.failed_rules = failed
        run.quality_score = score.score
        run.score_components = score.components
        run.accepted_output_path = accepted_key
        run.quarantine_output_path = quarantine_key
        run.duration_ms = round((time.perf_counter() - started) * 1000, 3)
        db.commit()
        db.refresh(run)
        logger.info(
            "validation_completed dataset_id=%s dataset_version_id=%s validation_run_id=%s rows=%s failed_rules=%s quality_score=%s duration_ms=%s",
            dataset_id,
            version_id,
            run.id,
            run.total_rows,
            run.failed_rules,
            run.quality_score,
            run.duration_ms,
        )
        return run
    except Exception as exc:
        db.rollback()
        persisted = db.get(ValidationRun, run.id)
        if persisted is not None:
            persisted.status = "failed"
            persisted.completed_at = datetime.now(UTC)
            persisted.error_message = str(exc)[:2000]
            persisted.duration_ms = round((time.perf_counter() - started) * 1000, 3)
            db.commit()
        logger.exception(
            "validation_failed dataset_id=%s dataset_version_id=%s validation_run_id=%s",
            dataset_id,
            version_id,
            run.id,
        )
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError("Validation execution failed.") from exc


def _evaluate_contract(
    frame: pl.DataFrame, version: DatasetVersion, contract: DataContract | None
) -> list[tuple[str, str | None, RuleEvaluation]]:
    if contract is None:
        return []
    rules = ContractRules.model_validate(contract.rules)
    logical_types = {column.column_name: column.logical_type for column in version.columns}
    context = ValidationContext(frame, logical_types, date.today(), set(rules.columns))
    evaluations: list[tuple[str, str | None, RuleEvaluation]] = []
    dataset_values = rules.dataset_rules.model_dump(exclude_none=True)
    for rule_type, value in dataset_values.items():
        if rule_type in {"forbid_unexpected_columns", "exact_schema"}:
            if not value:
                continue
            value = "exact" if rule_type == "exact_schema" else True
        if rule_type == "required_columns" and not value:
            continue
        code = f"dataset.{rule_type}"
        evaluations.append((code, None, evaluate_rule(rule_type, context, None, value)))
    for column_name, column_rules in rules.columns.items():
        for rule_type, value in column_rules.model_dump(exclude_none=True).items():
            if rule_type in {"required", "unique"} and not value:
                continue
            code = f"column.{column_name}.{rule_type}"
            evaluations.append(
                (code, column_name, evaluate_rule(rule_type, context, column_name, value))
            )
    return evaluations


def _result_model(
    run_id: uuid.UUID,
    code: str,
    column: str | None,
    evaluation: RuleEvaluation,
) -> ValidationResult:
    percentage = (
        evaluation.failure_count / evaluation.evaluated_count * 100
        if evaluation.evaluated_count
        else 0.0
    )
    return ValidationResult(
        validation_run_id=run_id,
        rule_code=code,
        rule_type=evaluation.rule_type,
        column_name=column,
        severity=evaluation.severity,
        status=evaluation.status,
        evaluated_count=evaluation.evaluated_count,
        failure_count=evaluation.failure_count,
        failure_percentage=round(percentage, 4),
        message=evaluation.message,
        details=evaluation.details,
    )


def _quarantine_batches(
    frame: pl.DataFrame,
    indexes: list[int],
    failures: dict[int, list[tuple[str, str]]],
    run_id: uuid.UUID,
    version_id: uuid.UUID,
    *,
    batch_size: int,
) -> Iterator[list[QuarantinedRow]]:
    for start in range(0, len(indexes), batch_size):
        batch_indexes = indexes[start : start + batch_size]
        rows = frame[batch_indexes].to_dicts()
        yield [
            QuarantinedRow(
                validation_run_id=run_id,
                dataset_version_id=version_id,
                source_row_number=index + 1,
                row_payload={key: _json_value(value) for key, value in row.items()},
                failed_rule_codes=[code for code, _ in failures[index]],
                failure_messages=[message for _, message in failures[index]],
            )
            for index, row in zip(batch_indexes, rows, strict=True)
        ]


def _json_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def get_validation_run(db: Session, run_id: uuid.UUID) -> ValidationRun | None:
    return db.get(ValidationRun, run_id)


def list_validation_results(
    db: Session, run_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[ValidationResult], int]:
    total = int(
        db.scalar(
            select(func.count()).select_from(ValidationResult).where(
                ValidationResult.validation_run_id == run_id
            )
        )
        or 0
    )
    items = list(
        db.scalars(
            select(ValidationResult)
            .where(ValidationResult.validation_run_id == run_id)
            .order_by(ValidationResult.created_at, ValidationResult.rule_code)
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return items, total


def list_quarantined_rows(
    db: Session, run_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[QuarantinedRow], int]:
    total = int(
        db.scalar(
            select(func.count()).select_from(QuarantinedRow).where(
                QuarantinedRow.validation_run_id == run_id
            )
        )
        or 0
    )
    items = list(
        db.scalars(
            select(QuarantinedRow)
            .where(QuarantinedRow.validation_run_id == run_id)
            .order_by(QuarantinedRow.source_row_number)
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return items, total
