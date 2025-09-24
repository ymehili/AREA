"""Pydantic schemas for ServiceConnection model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ServiceConnectionBase(BaseModel):
    """Base schema for ServiceConnection with common fields."""

    service_name: str = Field(..., min_length=1, max_length=255)


class ServiceConnectionCreate(ServiceConnectionBase):
    """Schema for creating a new ServiceConnection."""

    access_token: str = Field(..., min_length=1)
    refresh_token: Optional[str] = Field(None, min_length=1)
    expires_at: Optional[datetime] = None


class ServiceConnectionUpdate(ServiceConnectionBase):
    """Schema for updating an existing ServiceConnection."""

    access_token: Optional[str] = Field(None, min_length=1)
    refresh_token: Optional[str] = Field(None, min_length=1)
    expires_at: Optional[datetime] = None


class ServiceConnectionRead(ServiceConnectionBase):
    """Schema for reading a ServiceConnection with all fields."""

    id: uuid.UUID
    user_id: uuid.UUID
    encrypted_access_token: str
    encrypted_refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    oauth_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OAuthMetadata(BaseModel):
    """Schema for OAuth metadata."""

    provider: str
    user_info: Dict[str, Any]
    scopes: list[str]
    token_type: str = "Bearer"


__all__ = [
    "ServiceConnectionBase",
    "ServiceConnectionCreate",
    "ServiceConnectionRead",
    "ServiceConnectionUpdate",
    "OAuthMetadata",
]
