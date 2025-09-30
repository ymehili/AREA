"""API routes for service connections."""

from __future__ import annotations

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_active_user
from app.core.config import settings
from app.integrations.oauth.exceptions import OAuth2Error, UnsupportedProviderError
from app.integrations.oauth.factory import OAuth2ProviderFactory
from app.models.service_connection import ServiceConnection
from app.models.user import User
from app.schemas.service_connection import ServiceConnectionRead
from app.services.oauth_connections import OAuthConnectionService
from app.services.service_connections import DuplicateServiceConnectionError

router = APIRouter(tags=["service-connections"])
logger = logging.getLogger(__name__)


@router.post("/connect/{provider}")
async def initiate_service_connection(
    provider: str,
    request: Request,
    current_user: User = Depends(require_active_user),
) -> dict[str, str]:
    """Initiate OAuth connection flow for a service provider."""

    try:
        # Validate provider
        if provider not in OAuth2ProviderFactory.get_supported_providers():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )

        # Generate and store state in session
        state = OAuthConnectionService.generate_oauth_state()
        request.session[f"oauth_state_{provider}"] = state
        request.session["oauth_user_id"] = str(current_user.id)

        # Get authorization URL
        auth_url = OAuthConnectionService.get_authorization_url(provider, state)

        return {"authorization_url": auth_url}

    except UnsupportedProviderError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception("Failed to initiate OAuth connection for provider %s", provider)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate connection",
        )


@router.get("/callback/{provider}")
async def handle_service_connection_callback(
    provider: str,
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle OAuth callback for service connection."""

    try:
        # Handle OAuth error
        if error:
            return RedirectResponse(
                url=f"{settings.frontend_redirect_url_web}/connections?error={error}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        # Validate state parameter
        session_state = request.session.get(f"oauth_state_{provider}")
        if not session_state or session_state != state:
            return RedirectResponse(
                url=f"{settings.frontend_redirect_url_web}/connections?error=invalid_state",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        # Get user from session
        user_id = request.session.get("oauth_user_id")
        if not user_id:
            return RedirectResponse(
                url=f"{settings.frontend_redirect_url_web}/connections?error=session_expired",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        # Handle OAuth callback
        connection = await OAuthConnectionService.handle_oauth_callback(
            provider, code, user_id, db
        )

        # Clean up session
        request.session.pop(f"oauth_state_{provider}", None)
        request.session.pop("oauth_user_id", None)

        # Redirect to success page
        return RedirectResponse(
            url=f"{settings.frontend_redirect_url_web}/connections?success=connected&service={provider}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except DuplicateServiceConnectionError:
        logger.info("User %s already has connection for provider %s", user_id, provider)
        return RedirectResponse(
            url=f"{settings.frontend_redirect_url_web}/connections?error=already_connected&service={provider}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except OAuth2Error:
        logger.exception("OAuth error during callback for provider %s", provider)
        return RedirectResponse(
            url=f"{settings.frontend_redirect_url_web}/connections?error=connection_failed",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception:
        logger.exception("Unexpected error during OAuth callback for provider %s", provider)
        return RedirectResponse(
            url=f"{settings.frontend_redirect_url_web}/connections?error=unknown",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.get("/connections")
def list_user_connections(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[ServiceConnectionRead]:
    """List all service connections for the current user."""

    connections = (
        db.query(ServiceConnection)
        .filter(ServiceConnection.user_id == current_user.id)
        .all()
    )

    return [ServiceConnectionRead.model_validate(conn) for conn in connections]


@router.delete("/connections/{connection_id}")
def disconnect_service(
    connection_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Disconnect a service connection."""

    # Convert connection_id to UUID
    try:
        uuid_connection_id = uuid.UUID(connection_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid connection ID format",
        )

    connection = (
        db.query(ServiceConnection)
        .filter(
            ServiceConnection.id == uuid_connection_id,
            ServiceConnection.user_id == current_user.id,
        )
        .first()
    )

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found"
        )

    db.delete(connection)
    db.commit()

    return {"message": "Service disconnected successfully"}


@router.get("/providers")
def list_oauth_providers() -> dict[str, list[str]]:
    """List available OAuth providers."""
    return {"providers": OAuth2ProviderFactory.get_supported_providers()}


@router.get("/test/{provider}/{connection_id}")
async def test_provider_api_access(
    provider: str,
    connection_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Test API access for a specific service connection."""

    # Validate provider
    if provider not in OAuth2ProviderFactory.get_supported_providers():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}",
        )

    # Convert connection_id to UUID
    try:
        uuid_connection_id = uuid.UUID(connection_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid connection ID format",
        )

    # Get the connection
    connection = (
        db.query(ServiceConnection)
        .filter(
            ServiceConnection.id == uuid_connection_id,
            ServiceConnection.user_id == current_user.id,
            ServiceConnection.service_name == provider,
        )
        .first()
    )

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service connection not found",
        )

    try:
        # Get the OAuth provider
        oauth_provider = OAuth2ProviderFactory.create_provider(provider)

        # Decrypt the access token
        from app.core.encryption import decrypt_token
        access_token = decrypt_token(connection.encrypted_access_token)

        # Test API access based on provider
        if provider == "github":
            test_result = await oauth_provider.test_api_access(access_token)
        else:
            # For other providers, just validate the token
            is_valid = await oauth_provider.validate_token(access_token)
            test_result = {"token_valid": is_valid}

        return {
            "success": True,
            "provider": provider,
            "connection_id": connection_id,
            "test_result": test_result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API test failed: {str(e)}",
        )


__all__ = ["router"]
