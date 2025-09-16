"""Authentication-related Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a user via email/password registration."""

    email: EmailStr
    password: str = Field(min_length=8)

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)


class UserLogin(BaseModel):
    """Schema for logging in with email and password."""

    email: EmailStr
    password: str

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)


class UserRead(BaseModel):
    """Schema representing the public view of a user."""

    id: uuid.UUID
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, frozen=True)


class TokenResponse(BaseModel):
    """Schema for returning an access token to the client."""

    access_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(frozen=True)


__all__ = [
    "TokenResponse",
    "UserCreate",
    "UserLogin",
    "UserRead",
]
