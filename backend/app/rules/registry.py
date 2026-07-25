import re
from collections.abc import Callable
from datetime import date, datetime

import polars as pl

from backend.app.rules.base import RuleEvaluation, ValidationContext


RuleHandler = Callable[[ValidationContext, str | None, object], RuleEvaluation]
_REGISTRY: dict[str, RuleHandler] = {}


def register(rule_type: str) -> Callable[[RuleHandler], RuleHandler]:
    def decorator(handler: RuleHandler) -> RuleHandler:
        _REGISTRY[rule_type] = handler
        return handler

    return decorator


def evaluate_rule(
    rule_type: str, context: ValidationContext, column_name: str | None, value: object
) -> RuleEvaluation:
    try:
        handler = _REGISTRY[rule_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported validation rule: {rule_type}.") from exc
    return handler(context, column_name, value)


def supported_rule_types() -> set[str]:
    return set(_REGISTRY)


def _result(
    rule_type: str,
    passed: bool,
    evaluated: int,
    failures: int,
    message: str,
    invalid: list[int] | None = None,
    details: dict[str, object] | None = None,
    status: str | None = None,
) -> RuleEvaluation:
    return RuleEvaluation(
        rule_type=rule_type,
        passed=passed,
        status=status or ("passed" if passed else "failed"),
        severity="error",
        evaluated_count=evaluated,
        failure_count=failures,
        invalid_row_indexes=invalid or [],
        message=message,
        details=details or {},
    )


def _skip(rule_type: str, column: str) -> RuleEvaluation:
    return _result(rule_type, True, 0, 0, f"Column '{column}' is absent; rule skipped.", status="skipped")


def _column(context: ValidationContext, name: str | None, rule_type: str) -> pl.Series | None:
    if name is None:
        raise ValueError(f"Rule '{rule_type}' requires a column name.")
    return context.dataframe[name] if name in context.dataframe.columns else None


def _mask_result(rule_type: str, series: pl.Series, mask: pl.Series, message: str) -> RuleEvaluation:
    mask = mask.fill_null(False)
    indexes = mask.arg_true().to_list()
    return _result(rule_type, not indexes, len(series), len(indexes), message, indexes)


@register("minimum_row_count")
def minimum_row_count(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    minimum = int(value)
    actual = context.dataframe.height
    return _result("minimum_row_count", actual >= minimum, actual, max(minimum - actual, 0), f"Row count {actual} must be at least {minimum}.")


@register("maximum_row_count")
def maximum_row_count(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    maximum = int(value)
    actual = context.dataframe.height
    return _result("maximum_row_count", actual <= maximum, actual, max(actual - maximum, 0), f"Row count {actual} must be at most {maximum}.")


@register("maximum_duplicate_percentage")
def maximum_duplicate_percentage(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    maximum = float(value)
    duplicates = int(context.dataframe.is_duplicated().sum()) if context.dataframe.height else 0
    actual = duplicates / context.dataframe.height * 100 if context.dataframe.height else 0.0
    return _result("maximum_duplicate_percentage", actual <= maximum, context.dataframe.height, duplicates, f"Duplicate-row percentage {actual:.4f}% must be at most {maximum}%.", details={"actual_percentage": actual})


@register("required_columns")
def required_columns(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    required = {str(item) for item in value}  # type: ignore[union-attr]
    missing = sorted(required - set(context.dataframe.columns))
    return _result("required_columns", not missing, len(required), len(missing), "Required columns are present." if not missing else f"Missing required columns: {', '.join(missing)}.", details={"missing": missing})


@register("forbid_unexpected_columns")
@register("exact_schema")
def unexpected_columns(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    rule_type = "exact_schema" if value == "exact" else "forbid_unexpected_columns"
    unexpected = sorted(set(context.dataframe.columns) - context.expected_columns)
    return _result(rule_type, not unexpected, len(context.dataframe.columns), len(unexpected), "No unexpected columns." if not unexpected else f"Unexpected columns: {', '.join(unexpected)}.", details={"unexpected": unexpected})


@register("required")
def required_column(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    assert column is not None
    present = column in context.dataframe.columns
    return _result("required", present, 1, 0 if present else 1, f"Required column '{column}' {'is present' if present else 'is missing'}.")


@register("type")
def expected_type(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    assert column is not None
    if column not in context.dataframe.columns:
        return _skip("type", column)
    actual = context.logical_types.get(column, "unknown")
    expected = str(value)
    return _result("type", actual == expected, 1, 0 if actual == expected else 1, f"Column '{column}' type is {actual}; expected {expected}.", details={"actual": actual, "expected": expected})


@register("nullable")
def nullable(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    series = _column(context, column, "nullable")
    if series is None:
        return _skip("nullable", str(column))
    if bool(value):
        return _result("nullable", True, len(series), 0, f"Column '{column}' permits nulls.")
    return _mask_result("nullable", series, series.is_null(), f"Column '{column}' must not contain nulls.")


@register("unique")
def unique(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    series = _column(context, column, "unique")
    if series is None:
        return _skip("unique", str(column))
    return _mask_result("unique", series, series.is_duplicated() & series.is_not_null(), f"Column '{column}' must be unique.")


def _boundary(context: ValidationContext, column: str | None, value: object, *, minimum: bool) -> RuleEvaluation:
    rule_type = "minimum" if minimum else "maximum"
    series = _column(context, column, rule_type)
    if series is None:
        return _skip(rule_type, str(column))
    boundary: object = context.today if value == "today" else value
    logical_type = context.logical_types.get(str(column))
    if logical_type in {"date", "datetime"}:
        parsed = datetime.fromisoformat(str(boundary)).date() if not isinstance(boundary, date) else boundary
        comparable = series.cast(pl.Date)
        mask = comparable < parsed if minimum else comparable > parsed
    else:
        numeric = series.cast(pl.Float64, strict=False)
        limit = float(boundary)  # type: ignore[arg-type]
        mask = numeric < limit if minimum else numeric > limit
    return _mask_result(rule_type, series, mask, f"Column '{column}' violates its {rule_type} boundary.")


@register("minimum")
def minimum(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    return _boundary(context, column, value, minimum=True)


@register("maximum")
def maximum(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    return _boundary(context, column, value, minimum=False)


@register("minimum_length")
def minimum_length(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    series = _column(context, column, "minimum_length")
    if series is None:
        return _skip("minimum_length", str(column))
    mask = series.cast(pl.String).str.len_chars() < int(value)
    return _mask_result("minimum_length", series, mask, f"Column '{column}' contains values shorter than {value}.")


@register("maximum_length")
def maximum_length(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    series = _column(context, column, "maximum_length")
    if series is None:
        return _skip("maximum_length", str(column))
    mask = series.cast(pl.String).str.len_chars() > int(value)
    return _mask_result("maximum_length", series, mask, f"Column '{column}' contains values longer than {value}.")


@register("allowed_values")
def allowed_values(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    series = _column(context, column, "allowed_values")
    if series is None:
        return _skip("allowed_values", str(column))
    allowed = list(value)  # type: ignore[arg-type]
    return _mask_result("allowed_values", series, series.is_not_null() & ~series.is_in(allowed), f"Column '{column}' contains values outside the allowed set.")


@register("regex_pattern")
def regex_pattern(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    series = _column(context, column, "regex_pattern")
    if series is None:
        return _skip("regex_pattern", str(column))
    pattern = str(value)
    re.compile(pattern)
    mask = series.is_not_null() & ~series.cast(pl.String).str.contains(pattern)
    return _mask_result("regex_pattern", series, mask, f"Column '{column}' contains values that do not match the configured pattern.")


def _distinct(context: ValidationContext, column: str | None, value: object, *, minimum: bool) -> RuleEvaluation:
    rule_type = "minimum_distinct_count" if minimum else "maximum_distinct_count"
    series = _column(context, column, rule_type)
    if series is None:
        return _skip(rule_type, str(column))
    actual = series.n_unique()
    expected = int(value)
    passed = actual >= expected if minimum else actual <= expected
    return _result(rule_type, passed, len(series), 0 if passed else 1, f"Column '{column}' distinct count {actual} violates {rule_type}={expected}.", details={"actual": actual})


@register("minimum_distinct_count")
def minimum_distinct(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    return _distinct(context, column, value, minimum=True)


@register("maximum_distinct_count")
def maximum_distinct(context: ValidationContext, column: str | None, value: object) -> RuleEvaluation:
    return _distinct(context, column, value, minimum=False)
