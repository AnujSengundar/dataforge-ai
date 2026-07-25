import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

if TYPE_CHECKING:
    from backend.app.models.dataset_version import DatasetVersion


class DatasetProfile(Base):
    __tablename__ = "dataset_profiles"
    __table_args__ = (
        UniqueConstraint("dataset_version_id", name="uq_dataset_profiles_version"),
        CheckConstraint("row_count >= 0", name="ck_dataset_profiles_row_count_nonnegative"),
        CheckConstraint("column_count >= 0", name="ck_dataset_profiles_column_count_nonnegative"),
        CheckConstraint(
            "duplicate_row_count >= 0", name="ck_dataset_profiles_duplicate_count_nonnegative"
        ),
        CheckConstraint(
            "fully_null_row_count >= 0", name="ck_dataset_profiles_fully_null_count_nonnegative"
        ),
        CheckConstraint(
            "estimated_memory_bytes >= 0", name="ck_dataset_profiles_memory_nonnegative"
        ),
        CheckConstraint(
            "source_file_size_bytes >= 0", name="ck_dataset_profiles_file_size_nonnegative"
        ),
        CheckConstraint(
            "profiling_duration_ms >= 0", name="ck_dataset_profiles_duration_nonnegative"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_row_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duplicate_row_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    fully_null_row_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fully_null_row_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_memory_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    profiling_duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    profiled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    profile_summary: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False, default="profiling-v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    dataset_version: Mapped["DatasetVersion"] = relationship(
        "DatasetVersion", back_populates="profile"
    )

    @property
    def total_rows(self) -> int:
        return self.row_count

    @property
    def total_columns(self) -> int:
        return self.column_count

    @property
    def file_size_bytes(self) -> int:
        return self.source_file_size_bytes

    @property
    def execution_duration_ms(self) -> float:
        return self.profiling_duration_ms

    @property
    def generated_at(self) -> datetime:
        return self.profiled_at
