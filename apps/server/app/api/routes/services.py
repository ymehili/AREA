"""Service catalog API routes."""

from fastapi import APIRouter, Depends

from app.api.dependencies import require_active_user
from app.integrations.catalog import get_service_catalog
from app.schemas.services import ServiceCatalogResponse
from app.schemas.simple_services import ServiceSchema, ServiceListResponse
from app.services.variable_resolver import get_available_variables_for_service


router = APIRouter(tags=["services"])


@router.get(
    "/services",
    response_model=ServiceListResponse,
    dependencies=[Depends(require_active_user)],
)
def list_services() -> ServiceListResponse:
    """Return the list of available services."""
    services = get_service_catalog()
    service_list = [
        ServiceSchema(
            slug=service.slug,
            name=service.name,
            description=service.description
        )
        for service in services
    ]
    return ServiceListResponse(services=service_list)


@router.get(
    "/actions-reactions",
    response_model=ServiceCatalogResponse,
    dependencies=[Depends(require_active_user)],
)
def list_service_actions_reactions() -> ServiceCatalogResponse:
    """Return the catalog of automation actions and reactions."""

    return ServiceCatalogResponse.from_catalog(get_service_catalog())


@router.get(
    "/services/{service_id}/variables",
    dependencies=[Depends(require_active_user)],
)
def get_service_variables(service_id: str) -> list[str]:
    """Return the list of available variables for a specific service."""
    # For now, we'll pass an empty action_id since the function doesn't currently use it
    return get_available_variables_for_service(service_id, "")


__all__ = ["router"]
