"""Schemas for admin user management functionality."""

from __future__ import annotations

from typing import List, Optional
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from app.schemas.auth import UserRead


class AdminUserResponse(BaseModel):
    """Schema for admin user response with key information."""
    
    id: uuid.UUID
    email: str
    registration_date: datetime
    account_status: str  # 'Confirmed', 'Unconfirmed', etc.

    class Config:
        from_attributes = True


class PaginatedUserResponse(BaseModel):
    """Schema for paginated user response."""
    
    items: List[UserRead]
    total: int
    page: int
    limit: int
    pages: int