"""Pydantic schemas for ExecutionLog model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ExecutionStatus = Literal["Started", "Running", "Success", "Failed", "Pending"]


class ExecutionLogBase(BaseModel):
    """Base schema for ExecutionLog with common fields."""

    area_id: uuid.UUID
    status: ExecutionStatus = Field(...)
    output: Optional[str] = Field(None, max_length=5000)
    error_message: Optional[str] = Field(None, max_length=5000)
    step_details: Optional[dict] = None


class ExecutionLogCreate(ExecutionLogBase):
    """Schema for creating a new ExecutionLog."""

    pass


class ExecutionLogUpdate(BaseModel):
    """Schema for updating an existing ExecutionLog."""

    status: Optional[ExecutionStatus] = Field(None)
    output: Optional[str] = Field(None, max_length=5000)
    error_message: Optional[str] = Field(None, max_length=5000)
    step_details: Optional[dict] = None


class ExecutionLogResponse(ExecutionLogBase):
    """Schema for reading an ExecutionLog with all fields."""

    id: uuid.UUID
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "ExecutionLogBase",
    "ExecutionLogCreate",
    "ExecutionLogUpdate",
    "ExecutionLogResponse",
]