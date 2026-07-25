import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.dataset_column import DatasetColumnResponse


class DatasetProfileMetrics(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_count: int
    column_count: int
    duplicate_row_count: int
    duplicate_row_percentage: float
    fully_null_row_count: int
    fully_null_row_percentage: float
    estimated_memory_bytes: int
    source_file_size_bytes: int
    profiling_duration_ms: float
    profiled_at: datetime
    warnings: list[str]
    profile_summary: dict[str, object]
    engine_version: str
    created_at: datetime
    updated_at: datetime


class DatasetProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset_id: uuid.UUID | None = None
    id: uuid.UUID
    dataset_version_id: uuid.UUID
    row_count: int
    column_count: int
    duplicate_row_count: int
    duplicate_row_percentage: float
    fully_null_row_count: int
    fully_null_row_percentage: float
    estimated_memory_bytes: int
    source_file_size_bytes: int
    profiling_duration_ms: float
    profiled_at: datetime
    warnings: list[str]
    profile_summary: dict[str, object]
    engine_version: str
    created_at: datetime
    updated_at: datetime
    column_summary: dict[str, int] = {}
    columns: list[DatasetColumnResponse] = []
