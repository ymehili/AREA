"""ServiceConnection ORM model definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from sqlalchemy import DateTime, String, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover - used only for type checking
    from app.models.user import User


class ServiceConnection(Base):
    """Represents a connection between a user and a third-party service."""

    __tablename__ = "service_connections"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "service_name",
            name="uq_service_connections_user_id_service_name",
        ),
        Index("ix_service_connections_user_id", "user_id"),
        Index("ix_service_connections_service_name", "service_name"),
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
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(String(1024), nullable=False)
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    oauth_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="Provider-specific OAuth metadata"
    )

    # Relationship to User
    user: Mapped["User"] = relationship("User", back_populates="service_connections")


__all__ = ["ServiceConnection"]
