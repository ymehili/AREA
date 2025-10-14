"""Service catalog API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_active_user
from app.integrations.catalog import get_service_catalog
from app.models.user import User
from app.schemas.services import ServiceCatalogResponse
from app.schemas.simple_services import ServiceSchema, ServiceListResponse
from app.services.service_connections import get_user_service_connections
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
    """Return the catalog of automation actions and reactions.

    Filters services to only show:
    - Triggers (actions) that are implemented in schedulers (time, gmail)
    - Reactions that have registered handlers
    """
    from app.integrations.catalog import ServiceIntegration, AutomationOption
    from app.integrations.simple_plugins.registry import get_plugins_registry

    registry = get_plugins_registry()
    catalog = get_service_catalog()

    # Services with implemented triggers (via schedulers)
    implemented_triggers = {
        'time': ['every_interval'],  # Implemented in scheduler.py
        'gmail': ['new_email', 'new_email_from_sender', 'new_unread_email', 'email_starred'],  # Implemented in gmail_scheduler.py
        'outlook': ['new_email', 'new_email_from_sender', 'new_unread_email', 'email_important'],  # Implemented in outlook_scheduler.py
    }

    filtered_services = []
    for service in catalog:
        # Filter actions (triggers) to only implemented ones
        filtered_actions = []
        if service.slug in implemented_triggers:
            # Only include actions that are implemented
            for action in service.actions:
                if action.key in implemented_triggers[service.slug]:
                    filtered_actions.append(action)

        # Filter reactions to only those with handlers
        filtered_reactions = []
        for reaction in service.reactions:
            handler = registry.get_reaction_handler(service.slug, reaction.key)
            if handler is not None:
                filtered_reactions.append(reaction)

        # Only include service if it has at least one trigger or reaction
        if filtered_actions or filtered_reactions:
            filtered_service = ServiceIntegration(
                slug=service.slug,
                name=service.name,
                description=service.description,
                actions=tuple(filtered_actions),
                reactions=tuple(filtered_reactions)
            )
            filtered_services.append(filtered_service)

    return ServiceCatalogResponse.from_catalog(filtered_services)


@router.get(
    "/services/{service_id}/variables",
    dependencies=[Depends(require_active_user)],
)
def get_service_variables(service_id: str) -> list[str]:
    """Return the list of available variables for a specific service."""
    # For now, we'll pass an empty action_id since the function doesn't currently use it
    return get_available_variables_for_service(service_id, "")


@router.get(
    "/user-connections",
    dependencies=[Depends(require_active_user)],
)
def get_user_connected_services(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, list[str]]:
    """Return list of service slugs the current user has connected.

    Returns:
        Dictionary with 'connected_services' key containing list of service slugs
    """
    connections = get_user_service_connections(db, current_user.id)
    connected_service_slugs = [conn.service_name for conn in connections]
    return {"connected_services": connected_service_slugs}


__all__ = ["router"]
