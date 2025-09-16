"""Service catalog API routes."""

from fastapi import APIRouter, Depends

from app.api.dependencies import require_active_user
from app.integrations.catalog import get_service_catalog
from app.schemas.services import ServiceCatalogResponse


router = APIRouter(tags=["services"])


@router.get(
    "/actions-reactions",
    response_model=ServiceCatalogResponse,
    dependencies=[Depends(require_active_user)],
)
def list_service_actions_reactions() -> ServiceCatalogResponse:
    """Return the catalog of automation actions and reactions."""

    return ServiceCatalogResponse.from_catalog(get_service_catalog())


__all__ = ["router"]
