import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

if TYPE_CHECKING:
    from backend.app.models.dataset import Dataset
    from backend.app.models.dataset_column import DatasetColumn
    from backend.app.models.profile import DatasetProfile
    from backend.app.models.validation import ValidationRun


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version_number", name="uq_dataset_versions_number"),
        UniqueConstraint("dataset_id", "sha256_hash", name="uq_dataset_versions_hash"),
        Index("ix_dataset_versions_dataset_created", "dataset_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    row_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    ingestion_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingestion_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_signature: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    dataset: Mapped["Dataset"] = relationship(
        "Dataset", back_populates="versions", foreign_keys=[dataset_id]
    )
    columns: Mapped[list["DatasetColumn"]] = relationship(
        "DatasetColumn", back_populates="dataset_version", cascade="all, delete-orphan"
    )
    profile: Mapped["DatasetProfile | None"] = relationship(
        "DatasetProfile", back_populates="dataset_version", cascade="all, delete-orphan", uselist=False
    )
    validation_runs: Mapped[list["ValidationRun"]] = relationship(
        "ValidationRun", back_populates="dataset_version", cascade="all, delete-orphan"
    )
