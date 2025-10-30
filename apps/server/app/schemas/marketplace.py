"""Pydantic schemas for marketplace models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import bleach
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TemplatePublishRequest(BaseModel):
    """Schema for publishing a workflow as a template."""

    area_id: uuid.UUID
    title: str = Field(..., min_length=10, max_length=255)
    description: str = Field(..., min_length=50, max_length=1000)
    long_description: Optional[str] = Field(None, max_length=5000)
    category: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(..., min_length=1, max_length=10)

    @field_validator("title", "description", "long_description")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize text fields to prevent XSS attacks."""
        if v:
            return bleach.clean(v)
        return v

    @field_validator("tags")
    @classmethod
    def sanitize_tags(cls, v: List[str]) -> List[str]:
        """Clean and normalize tags."""
        return [tag.strip().lower() for tag in v if len(tag.strip()) >= 2]


class TemplateTagResponse(BaseModel):
    """Schema for template tag response."""

    id: uuid.UUID
    name: str
    slug: str
    usage_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateResponse(BaseModel):
    """Schema for reading a published template."""

    id: uuid.UUID
    original_area_id: Optional[uuid.UUID]
    publisher_user_id: uuid.UUID
    title: str
    description: str
    long_description: Optional[str]
    category: str
    tags: List[str] = Field(default_factory=list)
    template_json: Dict[str, Any]
    status: str
    visibility: str
    usage_count: int
    clone_count: int
    rating_average: Optional[float]
    rating_count: int
    created_at: datetime
    published_at: Optional[datetime]
    approved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> "TemplateResponse":
        """Custom validation to extract tag names from relationship."""
        if hasattr(obj, "tags") and obj.tags:
            # Extract tag names from TemplateTag objects
            tag_names = [tag.name for tag in obj.tags]
            # Create dict representation
            data = {
                "id": obj.id,
                "original_area_id": obj.original_area_id,
                "publisher_user_id": obj.publisher_user_id,
                "title": obj.title,
                "description": obj.description,
                "long_description": obj.long_description,
                "category": obj.category,
                "tags": tag_names,
                "template_json": obj.template_json,
                "status": obj.status,
                "visibility": obj.visibility,
                "usage_count": obj.usage_count,
                "clone_count": obj.clone_count,
                "rating_average": float(obj.rating_average) if obj.rating_average is not None else None,
                "rating_count": obj.rating_count,
                "created_at": obj.created_at,
                "published_at": obj.published_at,
                "approved_at": obj.approved_at,
            }
            return super().model_validate(data, **kwargs)
        return super().model_validate(obj, **kwargs)


class TemplateSearchParams(BaseModel):
    """Schema for template search and filter parameters."""

    q: Optional[str] = Field(None, max_length=100, description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    services: List[str] = Field(default_factory=list, description="Filter by services")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating filter")
    sort_by: str = Field(
        "usage_count",
        pattern="^(created_at|usage_count|rating_average|title)$",
        description="Sort field",
    )
    order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class TemplateCloneRequest(BaseModel):
    """Schema for cloning a template."""

    area_name: str = Field(..., min_length=1, max_length=255)
    parameter_overrides: Dict[str, Any] = Field(default_factory=dict)


class TemplateCloneResponse(BaseModel):
    """Schema for clone template response."""

    created_area_id: uuid.UUID
    message: str


class TemplateCategoryResponse(BaseModel):
    """Schema for template category response."""

    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str]
    icon: Optional[str]
    display_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateApprovalRequest(BaseModel):
    """Schema for approving or rejecting a template."""

    status: str = Field(..., pattern="^(approved|rejected)$")
    rejection_reason: Optional[str] = Field(None, max_length=500)


__all__ = [
    "TemplatePublishRequest",
    "TemplateResponse",
    "TemplateSearchParams",
    "TemplateCloneRequest",
    "TemplateCloneResponse",
    "TemplateCategoryResponse",
    "TemplateTagResponse",
    "TemplateApprovalRequest",
]
