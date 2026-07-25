import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
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


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"
    __table_args__ = (
        UniqueConstraint(
            "dataset_version_id", "column_name", name="uq_dataset_columns_version_name"
        ),
        UniqueConstraint(
            "dataset_version_id", "column_position", name="uq_dataset_columns_version_position"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    column_position: Mapped[int] = mapped_column(Integer, nullable=False)
    logical_type: Mapped[str] = mapped_column(String(50), nullable=False)
    physical_type: Mapped[str] = mapped_column(String(100), nullable=False)
    nullable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    null_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    non_null_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    null_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    distinct_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unique_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    sample_values: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    min_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mean_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    stddev_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_length: Mapped[float | None] = mapped_column(Float, nullable=True)
    earliest_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latest_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_constant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_fully_null: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_high_null: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_candidate_identifier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_possible_categorical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_possible_datetime_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_possible_numeric_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    top_values: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    dataset_version: Mapped["DatasetVersion"] = relationship(
        "DatasetVersion", back_populates="columns"
    )

    @property
    def inferred_data_type(self) -> str:
        return self.logical_type

    @property
    def unique_count(self) -> int:
        return self.distinct_count

    @property
    def unique_ratio(self) -> float:
        return self.unique_percentage / 100

    @property
    def dataset_id(self) -> uuid.UUID:
        return self.dataset_version.dataset_id
