import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatasetColumnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_version_id: uuid.UUID
    column_name: str
    column_position: int
    logical_type: str
    physical_type: str
    nullable: bool
    null_count: int
    non_null_count: int
    null_percentage: float
    distinct_count: int
    unique_percentage: float
    sample_values: list[str]
    min_value: str | None
    max_value: str | None
    mean_value: float | None
    median_value: float | None
    stddev_value: float | None
    min_length: int | None
    max_length: int | None
    avg_length: float | None
    earliest_value: str | None
    latest_value: str | None
    is_constant: bool
    is_fully_null: bool
    is_high_null: bool
    is_candidate_identifier: bool
    is_possible_categorical: bool
    is_possible_datetime_text: bool
    is_possible_numeric_text: bool
    top_values: list[dict[str, object]]
    created_at: datetime
    updated_at: datetime
