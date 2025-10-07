"""Pydantic schemas for UserActivityLog model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserActivityLogBase(BaseModel):
    """Base schema for UserActivityLog with common fields."""

    user_id: uuid.UUID
    action_type: str = Field(..., max_length=100)
    details: Optional[str] = Field(None, max_length=5000)
    service_name: Optional[str] = Field(None, max_length=100)


class UserActivityLogCreate(UserActivityLogBase):
    """Schema for creating a new UserActivityLog."""

    pass


class UserActivityLogUpdate(BaseModel):
    """Schema for updating an existing UserActivityLog."""

    action_type: Optional[str] = Field(None, max_length=100)
    details: Optional[str] = Field(None, max_length=5000)
    service_name: Optional[str] = Field(None, max_length=100)


class UserActivityLogResponse(UserActivityLogBase):
    """Schema for reading a UserActivityLog with all fields."""

    id: uuid.UUID
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "UserActivityLogBase",
    "UserActivityLogCreate",
    "UserActivityLogUpdate",
    "UserActivityLogResponse",
]