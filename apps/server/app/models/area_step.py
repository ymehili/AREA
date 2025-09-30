"""AreaStep ORM model definition for multi-step workflows."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, ForeignKey, Integer, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from app.models.area import Area


class AreaStepType(str, enum.Enum):
    """Enumeration of step types in a multi-step workflow."""

    ACTION = "action"
    REACTION = "reaction"
    CONDITION = "condition"
    DELAY = "delay"


class AreaStep(Base):
    """Represents a single step in a multi-step automation workflow."""

    __tablename__ = "area_steps"

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
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[AreaStepType] = mapped_column(
        SQLEnum(AreaStepType, name="areasteptype", native_enum=False),
        nullable=False,
    )
    service_slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config: Mapped[dict | None] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
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

    # Relationship to Area
    area: Mapped["Area"] = relationship("Area", back_populates="steps")


__all__ = ["AreaStep", "AreaStepType"]
