"""Pydantic schemas for API key connections."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ApiKeyConnectionBase(BaseModel):
    """Base schema for API key connections with common fields."""

    service_name: str = Field(..., min_length=1, max_length=255)


class ApiKeyConnectionCreateRequest(BaseModel):
    """Schema for API key creation request - doesn't require service_name since it comes from path parameter.
    
    Note: Service-specific validation (format, actual API validation) is done in the endpoint handler.
    """
    
    api_key: str = Field(..., min_length=1)


class ApiKeyConnectionCreate(ApiKeyConnectionBase):
    """Schema for creating a new API key connection.
    
    Note: Service-specific validation (format, actual API validation) is done in the endpoint handler.
    """

    api_key: str = Field(..., min_length=1)


class ApiKeyConnectionUpdate(ApiKeyConnectionBase):
    """Schema for updating an existing API key connection.
    
    Note: Service-specific validation (format, actual API validation) is done in the endpoint handler.
    """

    api_key: Optional[str] = Field(None, min_length=1)


class ApiKeyConnectionRead(ApiKeyConnectionBase):
    """Schema for reading an API key connection with masked key."""

    id: str
    user_id: str
    service_name: str
    masked_key: str  # Only return a masked version of the API key
    created_at: str
    updated_at: str


__all__ = [
    "ApiKeyConnectionBase",
    "ApiKeyConnectionCreate",
    "ApiKeyConnectionCreateRequest",
    "ApiKeyConnectionRead",
    "ApiKeyConnectionUpdate",
]