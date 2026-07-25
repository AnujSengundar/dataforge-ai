import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

if TYPE_CHECKING:
    from backend.app.models.dataset_version import DatasetVersion


class ValidationRun(Base):
    __tablename__ = "validation_runs"
    __table_args__ = (Index("ix_validation_runs_version_created", "dataset_version_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_contracts.id", ondelete="SET NULL"), nullable=True
    )
    contract_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    passed_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_components: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    accepted_output_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    quarantine_output_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dataset_version: Mapped["DatasetVersion"] = relationship(
        "DatasetVersion", back_populates="validation_runs"
    )
    results: Mapped[list["ValidationResult"]] = relationship(
        "ValidationResult", back_populates="validation_run", cascade="all, delete-orphan"
    )
    quarantined_rows: Mapped[list["QuarantinedRow"]] = relationship(
        "QuarantinedRow", back_populates="validation_run", cascade="all, delete-orphan"
    )


class ValidationResult(Base):
    __tablename__ = "validation_results"
    __table_args__ = (Index("ix_validation_results_run_status", "validation_run_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("validation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_code: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(100), nullable=False)
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    evaluated_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    failure_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    failure_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    validation_run: Mapped["ValidationRun"] = relationship("ValidationRun", back_populates="results")


class QuarantinedRow(Base):
    __tablename__ = "quarantined_rows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("validation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False
    )
    source_row_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    row_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    failed_rule_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    failure_messages: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    quarantined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    validation_run: Mapped["ValidationRun"] = relationship(
        "ValidationRun", back_populates="quarantined_rows"
    )
