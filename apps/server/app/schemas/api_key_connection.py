"""Pydantic schemas for API key connections."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, validator


class ApiKeyConnectionBase(BaseModel):
    """Base schema for API key connections with common fields."""

    service_name: str = Field(..., min_length=1, max_length=255)


class ApiKeyConnectionCreateRequest(BaseModel):
    """Schema for API key creation request - doesn't require service_name since it comes from path parameter."""
    
    api_key: str = Field(..., min_length=1)

    @validator("api_key")
    def validate_api_key_format(cls, v) -> str:
        """Validate that the API key starts with 'sk-' for OpenAI."""
        if not (v.startswith("sk-") or v.startswith("sk-proj-") or v.startswith("sk-svcacct-")):
            raise ValueError("API key must start with 'sk-', 'sk-proj-', or 'sk-svcacct-'")
        return v


class ApiKeyConnectionCreate(ApiKeyConnectionBase):
    """Schema for creating a new API key connection."""

    api_key: str = Field(..., min_length=1)

    @validator("api_key")
    def validate_api_key_format(cls, v) -> str:
        """Validate that the API key starts with 'sk-' for OpenAI."""
        if not (v.startswith("sk-") or v.startswith("sk-proj-") or v.startswith("sk-svcacct-")):
            raise ValueError("API key must start with 'sk-', 'sk-proj-', or 'sk-svcacct-'")
        return v


class ApiKeyConnectionUpdate(ApiKeyConnectionBase):
    """Schema for updating an existing API key connection."""

    api_key: Optional[str] = Field(None, min_length=1)

    @validator("api_key", pre=True, always=True)
    def validate_api_key_format(cls, v) -> Optional[str]:
        """Validate that the API key starts with 'sk-' for OpenAI."""
        if v is not None and not (v.startswith("sk-") or v.startswith("sk-proj-") or v.startswith("sk-svcacct-")):
            raise ValueError("API key must start with 'sk-', 'sk-proj-', or 'sk-svcacct-'")
        return v


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