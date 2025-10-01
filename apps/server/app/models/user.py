"""User ORM model definition."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.sql import expression
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.email_verification_token import EmailVerificationToken
    from app.models.service_connection import ServiceConnection
    from app.models.area import Area


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
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    google_oauth_sub: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_oauth_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    microsoft_oauth_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=expression.false(),
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    confirmation_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
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
    
    # Relationship to ServiceConnection
    service_connections: Mapped[List["ServiceConnection"]] = relationship(
        "ServiceConnection", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    email_verification_tokens: Mapped[List["EmailVerificationToken"]] = relationship(
        "EmailVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    # Relationship to Area
    areas: Mapped[List["Area"]] = relationship(
        "Area",
        back_populates="user",
        cascade="all, delete-orphan"
    )


__all__ = ["User"]
