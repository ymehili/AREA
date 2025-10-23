"""Pydantic schemas for admin audit logging."""

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class AdminAuditLogCreate(BaseModel):
    """Request schema for creating admin audit log entries."""

    admin_user_id: UUID
    target_user_id: UUID
    action_type: str
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminAuditLogResponse(BaseModel):
    """Response schema for admin audit log data."""

    id: UUID
    admin_user_id: UUID
    target_user_id: UUID
    action_type: str
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
