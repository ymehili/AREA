"""PublishedTemplate ORM model definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Numeric, func, event
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from app.models.area import Area
    from app.models.template_tag import TemplateTag
    from app.models.template_usage import TemplateUsage
    from app.models.user import User


class PublishedTemplate(Base):
    """Represents a published workflow template in the marketplace."""

    __tablename__ = "published_templates"
    __table_args__ = (
        Index("ix_published_templates_publisher", "publisher_user_id"),
        Index("ix_published_templates_category", "category"),
        Index("ix_published_templates_status", "status", "visibility"),
        Index("ix_published_templates_usage", "usage_count"),
        # Note: search_vector index is conditionally added for PostgreSQL only
        # See the after_create event listener below
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    original_area_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("areas.id", ondelete="SET NULL"), nullable=True
    )
    publisher_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Metadata
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    long_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Template content (sanitized workflow JSON)
    template_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", server_default="pending"
    )  # pending, approved, rejected, archived
    visibility: Mapped[str] = mapped_column(
        String(50), nullable=False, default="public", server_default="public"
    )  # public, private, unlisted
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Statistics
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    clone_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rating_average: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # Search vector (automatically updated by trigger in PostgreSQL, ignored in SQLite)
    # Note: This column is conditionally created only for PostgreSQL databases
    # SQLite will skip this column during table creation via conftest override

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    publisher: Mapped["User"] = relationship("User", foreign_keys=[publisher_user_id], viewonly=True)
    approved_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[approved_by_user_id], viewonly=True
    )
    original_area: Mapped[Optional["Area"]] = relationship("Area", viewonly=True)

    tags: Mapped[List["TemplateTag"]] = relationship(
        "TemplateTag",
        secondary="template_tag_mappings",
        back_populates="templates",
    )

    usage_records: Mapped[List["TemplateUsage"]] = relationship(
        "TemplateUsage",
        back_populates="template",
        cascade="all, delete-orphan",
    )


# Add search_vector column only for PostgreSQL databases
# This prevents SQLite test database errors
@event.listens_for(PublishedTemplate.__table__, "before_create")
def add_search_vector_column(target, connection, **kw):
    """Conditionally add search_vector column and index only for PostgreSQL."""
    if connection.dialect.name == "postgresql":
        from sqlalchemy import Column
        if not hasattr(target.c, "search_vector"):
            # Add the search_vector column
            target.append_column(
                Column("search_vector", TSVECTOR, nullable=True)
            )
            # Add GIN index on search_vector
            index = Index(
                "ix_published_templates_search",
                target.c.search_vector,
                postgresql_using="gin"
            )
            index.create(connection)
__all__ = ["PublishedTemplate"]
