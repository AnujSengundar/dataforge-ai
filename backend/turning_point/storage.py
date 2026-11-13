from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class Investigation(Base):
    __tablename__ = "turning_point_investigations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[str] = mapped_column(String(64))
    source_version: Mapped[str] = mapped_column(String(16))
    claim: Mapped[str] = mapped_column(String(400))
    level: Mapped[int]
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("turning_point_investigations.id"), index=True
    )
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
