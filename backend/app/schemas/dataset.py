import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    stored_filename: str
    file_path: str
    file_hash: str
    file_size_bytes: int
    row_count: int | None
    column_count: int | None
    status: str
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(BaseModel):
    datasets: list[DatasetResponse]
    count: int
