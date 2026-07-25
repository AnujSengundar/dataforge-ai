import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

if TYPE_CHECKING:
    from backend.app.models.dataset_column import DatasetColumn
    from backend.app.models.dataset_version import DatasetVersion
    from backend.app.models.data_contract import DataContract


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", use_alter=True, name="fk_datasets_current_version_id"),
        nullable=True,
    )
    # Retained as nullable compatibility fields for pre-v0.2 rows and /datasets/upload.
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    versions: Mapped[list["DatasetVersion"]] = relationship(
        "DatasetVersion",
        back_populates="dataset",
        cascade="all, delete-orphan",
        foreign_keys="DatasetVersion.dataset_id",
    )
    contracts: Mapped[list["DataContract"]] = relationship(
        "DataContract", back_populates="dataset", cascade="all, delete-orphan"
    )

    @property
    def columns(self) -> list["DatasetColumn"]:
        if not self.versions:
            return []
        return self.versions[-1].columns
