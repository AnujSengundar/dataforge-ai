import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DatasetRules(BaseModel):
    minimum_row_count: int | None = Field(default=None, ge=0)
    maximum_row_count: int | None = Field(default=None, ge=0)
    maximum_duplicate_percentage: float | None = Field(default=None, ge=0, le=100)
    required_columns: list[str] = Field(default_factory=list)
    forbid_unexpected_columns: bool = False
    exact_schema: bool = False


class ColumnRules(BaseModel):
    required: bool = False
    type: Literal["integer", "decimal", "boolean", "string", "date", "datetime", "categorical", "unknown"] | None = None
    nullable: bool | None = None
    unique: bool = False
    minimum: int | float | str | None = None
    maximum: int | float | str | None = None
    minimum_length: int | None = Field(default=None, ge=0)
    maximum_length: int | None = Field(default=None, ge=0)
    allowed_values: list[str | int | float | bool] | None = None
    regex_pattern: str | None = Field(default=None, max_length=500)
    minimum_distinct_count: int | None = Field(default=None, ge=0)
    maximum_distinct_count: int | None = Field(default=None, ge=0)


class ContractRules(BaseModel):
    dataset_rules: DatasetRules = Field(default_factory=DatasetRules)
    columns: dict[str, ColumnRules] = Field(default_factory=dict)


class ContractCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    rules: ContractRules
    active: bool = False


class ContractUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    rules: ContractRules | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "ContractUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one contract field must be supplied.")
        return self


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    version: int
    name: str
    description: str | None
    rules: dict[str, object]
    active: bool
    previous_version_id: uuid.UUID | None
    created_at: datetime
