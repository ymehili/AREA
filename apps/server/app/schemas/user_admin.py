"""Pydantic schemas for admin user management."""

from pydantic import BaseModel, ConfigDict
from typing import List
from uuid import UUID
from datetime import datetime


class AdminUserResponse(BaseModel):
    """Response schema for admin user data."""
    
    id: UUID
    email: str
    is_admin: bool
    created_at: datetime
    is_confirmed: bool
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedUserList(BaseModel):
    """Response schema for paginated user list."""
    
    users: List[AdminUserResponse]
    total_count: int
    skip: int
    limit: int