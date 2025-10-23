"""Pydantic schemas for admin user management."""

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
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


class UpdateAdminStatusRequest(BaseModel):
    """Request schema for updating user admin status."""

    is_admin: bool


class CreateUserAdminRequest(BaseModel):
    """Request schema for creating a user via admin panel."""

    email: str
    password: str = Field(min_length=8)
    is_admin: bool = False
    full_name: Optional[str] = None

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)


class SuspendUserRequest(BaseModel):
    """Request schema for suspending a user account."""

    reason: Optional[str] = Field(default=None, max_length=1000)

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)


class DeleteUserRequest(BaseModel):
    """Request schema for deleting a user account."""

    reason: Optional[str] = Field(default=None, max_length=1000)

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)
