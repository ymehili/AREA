"""Pydantic schemas for AreaStep model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AreaStepBase(BaseModel):
    """Base schema for AreaStep with common fields."""

    step_type: str = Field(..., min_length=1, max_length=50)
    order: int = Field(..., ge=0)
    service: Optional[str] = Field(None, max_length=255)
    action: Optional[str] = Field(None, max_length=255)
    config: Optional[Dict[str, Any]] = None


class AreaStepCreateInternal(AreaStepBase):
    """Schema for creating a new AreaStep internally (without area_id)."""

    @field_validator("step_type")
    @classmethod
    def validate_step_type(cls, v: str) -> str:
        """Validate step_type is one of the allowed values."""
        allowed_types = {"trigger", "action", "reaction", "condition", "delay"}
        if v not in allowed_types:
            raise ValueError(f"step_type must be one of {allowed_types}, got '{v}'")
        return v


class AreaStepCreate(AreaStepBase):
    """Schema for creating a new AreaStep via API (includes area_id) - can be used internally without area_id."""

    area_id: Optional[str] = None  # Optional to maintain backward compatibility

    @field_validator("step_type")
    @classmethod
    def validate_step_type(cls, v: str) -> str:
        """Validate step_type is one of the allowed values."""
        allowed_types = {"trigger", "action", "reaction", "condition", "delay"}
        if v not in allowed_types:
            raise ValueError(f"step_type must be one of {allowed_types}, got '{v}'")
        return v


class AreaStepUpdate(BaseModel):
    """Schema for updating an existing AreaStep."""

    step_type: Optional[str] = Field(None, min_length=1, max_length=50)
    order: Optional[int] = Field(None, ge=0)
    service: Optional[str] = Field(None, max_length=255)
    action: Optional[str] = Field(None, max_length=255)
    config: Optional[Dict[str, Any]] = None

    @field_validator("step_type")
    @classmethod
    def validate_step_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate step_type is one of the allowed values."""
        if v is None:
            return v
        allowed_types = {"trigger", "action", "reaction", "condition", "delay"}
        if v not in allowed_types:
            raise ValueError(f"step_type must be one of {allowed_types}, got '{v}'")
        return v


class AreaStepResponse(AreaStepBase):
    """Schema for reading an AreaStep with all fields."""

    id: uuid.UUID
    area_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "AreaStepBase",
    "AreaStepCreate",
    "AreaStepUpdate",
    "AreaStepResponse",
]
