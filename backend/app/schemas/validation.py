import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ValidationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
    contract_id: uuid.UUID | None
    contract_version: int | None
    status: str
    started_at: datetime
    completed_at: datetime | None
    total_rows: int
    valid_rows: int
    invalid_rows: int
    passed_rules: int
    failed_rules: int
    quality_score: float | None
    score_components: dict[str, object]
    duration_ms: float | None
    error_message: str | None


class ValidationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    validation_run_id: uuid.UUID
    rule_code: str
    rule_type: str
    column_name: str | None
    severity: str
    status: str
    evaluated_count: int
    failure_count: int
    failure_percentage: float
    message: str
    details: dict[str, object]
    created_at: datetime


class QuarantinedRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    validation_run_id: uuid.UUID
    dataset_version_id: uuid.UUID
    source_row_number: int
    row_payload: dict[str, object]
    failed_rule_codes: list[str]
    failure_messages: list[str]
    quarantined_at: datetime


class PaginatedValidationResults(BaseModel):
    items: list[ValidationResultResponse]
    total: int
    limit: int
    offset: int


class PaginatedQuarantine(BaseModel):
    items: list[QuarantinedRowResponse]
    total: int
    limit: int
    offset: int
