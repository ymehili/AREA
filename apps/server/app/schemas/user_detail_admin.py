"""Extended user detail schema for admin view."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ServiceConnectionForUserDetail(BaseModel):
    """Schema for service connection data in user detail view."""
    
    id: UUID
    service_name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AreaForUserDetail(BaseModel):
    """Schema for area data in user detail view."""
    
    id: UUID
    name: str
    trigger_service: str
    reaction_service: str
    enabled: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserDetailAdminResponse(BaseModel):
    """Extended user detail schema for admin view."""
    
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_confirmed: bool
    is_admin: bool
    is_suspended: bool
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    
    # Include connected services
    service_connections: List[ServiceConnectionForUserDetail] = []
    
    # Include user's created AREAs
    areas: List[AreaForUserDetail] = []
    
    model_config = ConfigDict(from_attributes=True)