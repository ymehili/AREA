"""Pydantic schemas for simplified service listings."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ServiceSchema(BaseModel):
    """Schema representing a service integration without actions/reactions."""

    slug: str
    name: str
    description: str

    model_config = ConfigDict(frozen=True)


class ServiceListResponse(BaseModel):
    """Schema describing a list of available service integrations."""

    services: list[ServiceSchema]

    model_config = ConfigDict(frozen=True)


__all__ = [
    "ServiceSchema",
    "ServiceListResponse",
]
