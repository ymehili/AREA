"""Area ORM model definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from app.models.area_step import AreaStep
    from app.models.execution_log import ExecutionLog
    from app.models.user import User


class Area(Base):
    """Represents an automation created by a user (Action-ReAction)."""

    __tablename__ = "areas"
    __table_args__ = (
        Index("ix_areas_user_id", "user_id"),
        UniqueConstraint("user_id", "name", name="uq_areas_user_id_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_service: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_action: Mapped[str] = mapped_column(String(255), nullable=False)
    reaction_service: Mapped[str] = mapped_column(String(255), nullable=False)
    reaction_action: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_params: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    reaction_params: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default='true',
    )
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

    # Relationship to User
    user: Mapped["User"] = relationship("User", back_populates="areas")

    # Relationship to ExecutionLog
    execution_logs: Mapped[list["ExecutionLog"]] = relationship(
        "ExecutionLog",
        back_populates="area",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Relationship to AreaStep
    steps: Mapped[List["AreaStep"]] = relationship(
        "AreaStep",
        back_populates="area",
        order_by="AreaStep.order",
        cascade="all, delete-orphan",
    )


__all__ = ["Area"]