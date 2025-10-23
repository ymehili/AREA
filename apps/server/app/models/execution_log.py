"""ExecutionLog ORM model definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from app.models.area import Area


class ExecutionLog(Base):
    """Represents execution logs for AREA automation runs."""

    __tablename__ = "execution_logs"
    __table_args__ = (
        Index("ix_execution_logs_area_id", "area_id"),
        Index("ix_execution_logs_timestamp", "timestamp"),
        Index("ix_execution_logs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("areas.id", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    output: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    step_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship to Area
    area: Mapped["Area"] = relationship("Area", back_populates="execution_logs")


__all__ = ["ExecutionLog"]
