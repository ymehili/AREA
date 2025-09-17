"""Area ORM model definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, ForeignKey, Index, UniqueConstraint, func, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
if TYPE_CHECKING:  # pragma: no cover - used only for type checking
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


__all__ = ["Area"]