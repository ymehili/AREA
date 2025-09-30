"""Pydantic schemas for Area model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AreaStepBase(BaseModel):
    """Base schema for AreaStep with common fields."""

    position: int = Field(..., ge=0)
    step_type: Literal["action", "reaction", "condition", "delay"]
    service_slug: Optional[str] = Field(None, min_length=1, max_length=255)
    action_key: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[dict[str, Any]] = None


class AreaStepCreate(AreaStepBase):
    """Schema for creating a new AreaStep."""

    @model_validator(mode="after")
    def validate_step_fields(self) -> "AreaStepCreate":
        """Validate that ACTION/REACTION steps have required fields."""
        if self.step_type in ("action", "reaction"):
            if not self.service_slug or not self.action_key:
                raise ValueError(
                    f"service_slug and action_key are required for {self.step_type} steps"
                )
        elif self.step_type in ("condition", "delay"):
            if self.service_slug or self.action_key:
                raise ValueError(
                    f"service_slug and action_key should not be provided for {self.step_type} steps"
                )
        return self


class AreaStepUpdate(BaseModel):
    """Schema for updating an existing AreaStep."""

    position: Optional[int] = Field(None, ge=0)
    step_type: Optional[Literal["action", "reaction", "condition", "delay"]] = None
    service_slug: Optional[str] = Field(None, min_length=1, max_length=255)
    action_key: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[dict[str, Any]] = None


class AreaStepResponse(AreaStepBase):
    """Schema for reading an AreaStep with all fields."""

    id: uuid.UUID
    area_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AreaBase(BaseModel):
    """Base schema for Area with common fields."""

    name: str = Field(..., min_length=1, max_length=255)


class AreaCreate(AreaBase):
    """Schema for creating a new Area.

    NOTE: This schema now uses multi-step workflows. Each area must have at least
    one step, and the first step must be an ACTION type.
    """

    steps: list[AreaStepCreate] = Field(..., min_length=1)

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, steps: list[AreaStepCreate]) -> list[AreaStepCreate]:
        """Validate step list requirements."""
        if not steps:
            raise ValueError("At least one step is required")

        # Ensure first step is ACTION
        if steps[0].step_type != "action":
            raise ValueError("First step must be of type 'action'")

        # Validate positions are sequential starting from 0
        positions = [step.position for step in steps]
        expected_positions = list(range(len(steps)))
        if positions != expected_positions:
            raise ValueError(
                f"Step positions must be sequential starting from 0. "
                f"Expected {expected_positions}, got {positions}"
            )

        # Check for duplicate positions
        if len(positions) != len(set(positions)):
            raise ValueError("Duplicate step positions are not allowed")

        return steps


class AreaUpdate(BaseModel):
    """Schema for updating an existing Area."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    enabled: Optional[bool] = None
    steps: Optional[list[AreaStepCreate]] = None

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, steps: Optional[list[AreaStepCreate]]) -> Optional[list[AreaStepCreate]]:
        """Validate step list requirements if provided."""
        if steps is None:
            return None

        if not steps:
            raise ValueError("At least one step is required")

        # Ensure first step is ACTION
        if steps[0].step_type != "action":
            raise ValueError("First step must be of type 'action'")

        # Validate positions are sequential starting from 0
        positions = [step.position for step in steps]
        expected_positions = list(range(len(steps)))
        if positions != expected_positions:
            raise ValueError(
                f"Step positions must be sequential starting from 0. "
                f"Expected {expected_positions}, got {positions}"
            )

        return steps


class AreaResponse(AreaBase):
    """Schema for reading an Area with all fields."""

    id: uuid.UUID
    user_id: uuid.UUID
    enabled: bool
    steps: list[AreaStepResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "AreaStepBase",
    "AreaStepCreate",
    "AreaStepUpdate",
    "AreaStepResponse",
    "AreaBase",
    "AreaCreate",
    "AreaUpdate",
    "AreaResponse",
]