"""Pydantic schemas powering profile management routes."""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginMethodStatus(BaseModel):
    """Represents whether a third-party login method is linked."""

    provider: str
    linked: bool
    identifier: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class UserProfileResponse(BaseModel):
    """Serialized profile data for the authenticated user."""

    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_confirmed: bool
    has_password: bool
    is_admin: bool
    login_methods: list[LoginMethodStatus]

    model_config = ConfigDict(frozen=True)


class UserProfileUpdate(BaseModel):
    """Incoming payload for updating profile fields."""

    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)


class PasswordChangeRequest(BaseModel):
    """Payload required to change a password."""

    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

    model_config = ConfigDict(frozen=True)


class LoginMethodLinkRequest(BaseModel):
    """Payload for linking an external login provider."""

    identifier: str = Field(..., min_length=1, max_length=255)

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)


__all__ = [
    "LoginMethodLinkRequest",
    "LoginMethodStatus",
    "PasswordChangeRequest",
    "UserProfileResponse",
    "UserProfileUpdate",
]
