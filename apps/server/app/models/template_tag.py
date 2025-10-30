"""TemplateTag ORM model and association table definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Table, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from app.models.marketplace_template import PublishedTemplate


# Association table for many-to-many relationship between templates and tags
template_tag_mappings = Table(
    "template_tag_mappings",
    Base.metadata,
    Column(
        "template_id",
        UUID(as_uuid=True),
        ForeignKey("published_templates.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("template_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
)


class TemplateTag(Base):
    """Represents a tag for categorizing and filtering templates."""

    __tablename__ = "template_tags"
    __table_args__ = (Index("ix_template_tags_name", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship to PublishedTemplate
    templates: Mapped[List["PublishedTemplate"]] = relationship(
        "PublishedTemplate",
        secondary=template_tag_mappings,
        back_populates="tags",
    )


__all__ = ["TemplateTag", "template_tag_mappings"]
