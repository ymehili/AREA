"""TemplateUsage ORM model definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from app.models.area import Area
    from app.models.marketplace_template import PublishedTemplate
    from app.models.user import User


class TemplateUsage(Base):
    """Tracks when users clone templates from the marketplace."""

    __tablename__ = "template_usage"
    __table_args__ = (
        Index("ix_template_usage_template", "template_id"),
        Index("ix_template_usage_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("published_templates.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_area_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("areas.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    template: Mapped["PublishedTemplate"] = relationship("PublishedTemplate", back_populates="usage_records")
    user: Mapped["User"] = relationship("User", viewonly=True)
    created_area: Mapped[Optional["Area"]] = relationship("Area", viewonly=True)


__all__ = ["TemplateUsage"]
