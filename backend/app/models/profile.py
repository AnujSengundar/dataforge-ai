import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

if TYPE_CHECKING:
    from backend.app.models.dataset_version import DatasetVersion


class DatasetProfile(Base):
    __tablename__ = "dataset_profiles"
    __table_args__ = (UniqueConstraint("dataset_version_id", name="uq_dataset_profiles_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_rows: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_columns: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_row_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duplicate_row_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    fully_null_row_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    estimated_memory_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    execution_duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dataset_version: Mapped["DatasetVersion"] = relationship(
        "DatasetVersion", back_populates="profile"
    )
