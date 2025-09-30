"""Pydantic schemas for Area model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AreaBase(BaseModel):
    """Base schema for Area with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    trigger_service: str = Field(..., min_length=1, max_length=255)
    trigger_action: str = Field(..., min_length=1, max_length=255)
    reaction_service: str = Field(..., min_length=1, max_length=255)
    reaction_action: str = Field(..., min_length=1, max_length=255)
    trigger_params: Optional[dict] = None
    reaction_params: Optional[dict] = None


class AreaCreate(AreaBase):
    """Schema for creating a new Area."""


class AreaUpdate(BaseModel):
    """Schema for updating an existing Area."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    trigger_service: Optional[str] = Field(None, min_length=1, max_length=255)
    trigger_action: Optional[str] = Field(None, min_length=1, max_length=255)
    reaction_service: Optional[str] = Field(None, min_length=1, max_length=255)
    reaction_action: Optional[str] = Field(None, min_length=1, max_length=255)
    trigger_params: Optional[dict] = None
    reaction_params: Optional[dict] = None
    enabled: Optional[bool] = None


class AreaResponse(AreaBase):
    """Schema for reading an Area with all fields."""

    id: uuid.UUID
    user_id: uuid.UUID
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "AreaBase",
    "AreaCreate",
    "AreaUpdate",
    "AreaResponse",
]