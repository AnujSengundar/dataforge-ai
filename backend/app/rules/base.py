from dataclasses import dataclass, field
from datetime import date

import polars as pl


@dataclass(frozen=True)
class ValidationContext:
    dataframe: pl.DataFrame
    logical_types: dict[str, str]
    today: date
    expected_columns: set[str]


@dataclass(frozen=True)
class RuleEvaluation:
    rule_type: str
    passed: bool
    status: str
    severity: str
    evaluated_count: int
    failure_count: int
    invalid_row_indexes: list[int] = field(default_factory=list)
    message: str = ""
    details: dict[str, object] = field(default_factory=dict)
