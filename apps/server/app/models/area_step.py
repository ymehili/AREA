"""AreaStep ORM model definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, String, Integer, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from app.models.area import Area


class AreaStep(Base):
    """Represents a single step in a multi-step automation workflow."""

    __tablename__ = "area_steps"
    __table_args__ = (
        UniqueConstraint(
            "area_id",
            "order",
            name="uq_area_steps_area_id_order",
        ),
        Index("ix_area_steps_area_id", "area_id"),
        Index("ix_area_steps_area_id_order", "area_id", "order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("areas.id"),
        nullable=False,
    )
    step_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Step type: action, reaction, condition, or delay",
    )
    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Execution order within the area (0-based)",
    )
    service: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Service name (NULL for delay/condition steps)",
    )
    action: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Action identifier within the service",
    )
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Step-specific configuration (e.g., delay duration, condition logic)",
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


__all__ = ["AreaStep"]
