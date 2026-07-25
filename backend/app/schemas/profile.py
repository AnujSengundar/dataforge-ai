import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.dataset_column import DatasetColumnResponse


class DatasetProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_version_id: uuid.UUID
    total_rows: int
    total_columns: int
    duplicate_row_count: int
    duplicate_row_percentage: float
    fully_null_row_count: int
    estimated_memory_bytes: int
    file_size_bytes: int
    execution_duration_ms: float
    generated_at: datetime
    columns: list[DatasetColumnResponse] = []
