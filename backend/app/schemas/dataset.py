import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    status: str
    current_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(BaseModel):
    items: list[DatasetResponse]
    total: int
    limit: int
    offset: int


class DatasetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    version_number: int
    original_filename: str
    file_format: str
    file_size_bytes: int
    sha256_hash: str
    row_count: int | None
    column_count: int | None
    processing_status: str
    ingestion_started_at: datetime | None
    ingestion_completed_at: datetime | None
    created_at: datetime
    error_message: str | None
    schema_signature: str | None


class DatasetVersionListResponse(BaseModel):
    items: list[DatasetVersionResponse]
    total: int
    limit: int
    offset: int


class UploadVersionResponse(BaseModel):
    dataset_id: uuid.UUID
    dataset_version_id: uuid.UUID
    version_number: int
    status: str
    duplicate: bool
    profile_available: bool
