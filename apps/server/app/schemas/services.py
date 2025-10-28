"""Pydantic schemas describing service automation catalogs."""

from __future__ import annotations

from typing import Sequence, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict

from app.integrations.catalog import ServiceIntegration


class AutomationOptionSchema(BaseModel):
    """Schema representing an individual automation action or reaction."""

    key: str
    name: str
    description: str
    params: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(frozen=True, from_attributes=True)


class ServiceDefinitionSchema(BaseModel):
    """Schema wrapping the available automation catalog for a service."""

    slug: str
    name: str
    description: str
    actions: list[AutomationOptionSchema]
    reactions: list[AutomationOptionSchema]

    model_config = ConfigDict(frozen=True)


class ServiceCatalogResponse(BaseModel):
    """Schema describing the full set of supported service integrations."""

    services: list[ServiceDefinitionSchema]

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_catalog(cls, services: Sequence[ServiceIntegration]) -> "ServiceCatalogResponse":
        """Build a schema response from catalog dataclasses."""

        service_payload = [
            ServiceDefinitionSchema(
                slug=service.slug,
                name=service.name,
                description=service.description,
                actions=[
                    AutomationOptionSchema.model_validate(action)
                    for action in service.actions
                ],
                reactions=[
                    AutomationOptionSchema.model_validate(reaction)
                    for reaction in service.reactions
                ],
            )
            for service in services
        ]
        return cls(services=service_payload)


__all__ = [
    "AutomationOptionSchema",
    "ServiceDefinitionSchema",
    "ServiceCatalogResponse",
]

