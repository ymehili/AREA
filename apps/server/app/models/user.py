"""User ORM model definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """Represents an application user."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("google_oauth_sub", name="uq_users_google_oauth_sub"),
        UniqueConstraint("github_oauth_id", name="uq_users_github_oauth_id"),
        UniqueConstraint("microsoft_oauth_id", name="uq_users_microsoft_oauth_id"),
        Index("ix_users_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    google_oauth_sub: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_oauth_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    microsoft_oauth_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
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


__all__ = ["User"]
