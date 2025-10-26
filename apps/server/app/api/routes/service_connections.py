"""API routes for service connections."""

import logging
import uuid
import httpx
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.background import BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_active_user
from app.core.config import settings
from app.core.encryption import encrypt_token
from app.integrations.oauth.exceptions import OAuth2Error, UnsupportedProviderError
from app.integrations.oauth.factory import OAuth2ProviderFactory
from app.models.service_connection import ServiceConnection
from app.models.user import User
from app.schemas.service_connection import ServiceConnectionRead
from app.services.oauth_connections import OAuthConnectionService
from app.services.service_connections import (
    DuplicateServiceConnectionError,
    get_service_connection_by_user_and_service,
    create_service_connection as create_oauth_service_connection,
    get_user_service_connections
)
from app.services.user_activity_logs import create_user_activity_log, log_user_activity_task
from app.schemas.user_activity_log import UserActivityLogCreate

# Import the new service connection schemas
from app.schemas.api_key_connection import ApiKeyConnectionCreate, ApiKeyConnectionCreateRequest

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create a router instance
router = APIRouter(tags=["service-connections"])
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


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
    background_tasks: BackgroundTasks,
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

        # Schedule service connection activity log using background task
        # so that if logging fails, the main operation is still successful
        background_tasks.add_task(
            log_user_activity_task,
            user_id=user_id,
            action_type="service_connected",
            details=f"User connected {provider} service",
            service_name=provider.title(),
            status="success"
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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Disconnect a service connection by ID."""

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

    # Schedule service disconnection activity log using background task
    # so that if logging fails, the main operation is still successful
    background_tasks.add_task(
        log_user_activity_task,
        user_id=str(current_user.id),
        action_type="service_disconnected",
        details=f"User disconnected {connection.service_name} service",
        service_name=connection.service_name,
        status="success"
    )

    db.delete(connection)
    db.commit()

    return {"message": "Service disconnected successfully"}


@router.delete("/disconnect/{service_name}")
async def disconnect_service_by_name(
    service_name: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Disconnect a service connection by service name.

    This endpoint allows users to easily disconnect a service by name (e.g., 'github', 'gmail')
    without needing to know the connection ID. This is useful when reconnecting to force
    a fresh OAuth flow with updated scopes.

    For GitHub, this also revokes the OAuth token on GitHub's side using their API,
    ensuring the token is completely invalidated.
    """

    connection = (
        db.query(ServiceConnection)
        .filter(
            ServiceConnection.service_name == service_name,
            ServiceConnection.user_id == current_user.id,
        )
        .first()
    )

    if not connection:
        # Return success even if not found - idempotent operation
        # This allows "disconnect then connect" to work smoothly
        return {"message": f"No {service_name} connection found (already disconnected)"}

    # For GitHub, revoke the token on GitHub's side before deleting from our database
    if service_name == "github":
        try:
            from app.core.encryption import decrypt_token
            from app.integrations.oauth.factory import OAuth2ProviderFactory

            # Decrypt the access token
            access_token = decrypt_token(connection.encrypted_access_token)

            # Get the GitHub provider and revoke the token
            provider = OAuth2ProviderFactory.create_provider("github")
            if hasattr(provider, 'revoke_token'):
                revoked = await provider.revoke_token(access_token)
                logger.info(
                    f"GitHub token revocation {'succeeded' if revoked else 'failed'} for user {current_user.id}"
                )
        except Exception as e:
            # Log the error but continue with disconnection
            # We don't want to block disconnection if revocation fails
            logger.error(f"Failed to revoke GitHub token: {e}", exc_info=True)

    # Schedule service disconnection activity log using background task
    background_tasks.add_task(
        log_user_activity_task,
        user_id=str(current_user.id),
        action_type="service_disconnected",
        details=f"User disconnected {connection.service_name} service",
        service_name=connection.service_name,
        status="success"
    )

    db.delete(connection)
    db.commit()

    return {"message": f"{service_name} service disconnected successfully"}


@router.get("/providers")
def list_oauth_providers() -> dict[str, list[str]]:
    """List available OAuth providers."""
    return {"providers": OAuth2ProviderFactory.get_supported_providers()}


@router.get("/test/{provider}/{connection_id}")
@limiter.limit("10/minute")  # Limit to 10 requests per minute per IP address
async def test_provider_api_access(
    provider: str,
    connection_id: str,
    request: Request,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Test API access for a specific service connection."""

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
        # Check if this is an OAuth provider
        if provider in OAuth2ProviderFactory.get_supported_providers():
            # Handle OAuth provider testing
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
        else:
            # Handle API key provider testing (e.g., OpenAI)
            # For API key services, check if the connection has been marked as API key connection
            if connection.oauth_metadata and connection.oauth_metadata.get("connection_type") == "api_key":
                # Import the OpenAI test logic based on the OpenAI plugin
                if provider == "openai":
                    from app.core.encryption import decrypt_token
                    import httpx
                    
                    # Decrypt the API key
                    api_key = decrypt_token(connection.encrypted_access_token)
                    
                    # Test the API key by making a simple request to the OpenAI API
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            "https://api.openai.com/v1/models",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=10.0
                        )
                        
                        if response.status_code == 200:
                            test_result = {"token_valid": True}
                        else:
                            error_detail = f"API test failed with status {response.status_code}"
                            if response.status_code == 401:
                                error_detail = "Authentication failed. Invalid OpenAI API key."
                            elif response.status_code == 429:
                                error_detail = "Rate limit exceeded. Please check your OpenAI usage limits."
                            elif response.status_code == 403:
                                error_detail = "Access forbidden. Please verify your OpenAI API key permissions."
                            
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=error_detail
                            )
                        
                        return {
                            "success": True,
                            "provider": provider,
                            "connection_id": connection_id,
                            "test_result": test_result,
                        }
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"API key testing not supported for provider: {provider}",
                    )
            else:
                # Provider not in supported OAuth providers and not an API key connection
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported provider: {provider}",
                )

    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API test failed: {str(e)}",
        )


@router.post("/api-key/{provider}")
@limiter.limit("5/minute")  # Limit to 5 requests per minute per IP address
async def add_api_key_connection(
    provider: str,
    api_key_connection: ApiKeyConnectionCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Add a new service connection using an API key instead of OAuth flow.
    
    This endpoint allows users to manually input API keys for services that don't use OAuth,
    such as OpenAI. The API key will be validated before storing in the database.
    
    Args:
        provider: The service provider slug (e.g., 'openai')
        api_key_connection: The API key in request body
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Connection details with success status
    """
    # Validate provider name - support for OpenAI, Weather, and DeepL
    supported_providers = ["openai", "weather", "deepl"]
    if provider not in supported_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API key connection not supported for provider: {provider}. Supported providers: {', '.join(supported_providers)}",
        )
    
    api_key = api_key_connection.api_key
    
    # Validate and test the API key based on the provider
    if provider == "openai":
        # Validate the API key format (OpenAI keys start with 'sk-', 'sk-proj-', or 'sk-svcacct-')
        if not (api_key.startswith("sk-") or api_key.startswith("sk-proj-") or api_key.startswith("sk-svcacct-")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid API key format. OpenAI API keys must start with 'sk-', 'sk-proj-', or 'sk-svcacct-'",
            )
        
        # Test the API key by making a simple request to the OpenAI API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                if response.status_code != 200:
                    error_detail = "Invalid API key or API error. Please check your API key and try again."
                    if response.status_code == 401:
                        error_detail = "Authentication failed. Invalid OpenAI API key."
                    elif response.status_code == 429:
                        error_detail = "Rate limit exceeded. Please check your OpenAI usage limits."
                    elif response.status_code == 403:
                        error_detail = "Access forbidden. Please verify your OpenAI API key permissions."
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_detail
                    )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Request timed out while validating the API key with OpenAI service. Please try again later."
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to validate API key with OpenAI service: {str(e)}"
            )
    
    elif provider == "weather":
        # Validate the API key format (OpenWeatherMap keys are 32 alphanumeric characters)
        if len(api_key) != 32 or not api_key.isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid API key format. OpenWeatherMap API keys should be 32 alphanumeric characters.",
            )
        
        # Test the API key by making a simple request to the OpenWeatherMap API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"q": "London", "appid": api_key},
                    timeout=10.0
                )
                if response.status_code != 200:
                    error_detail = "Invalid API key or API error. Please check your OpenWeatherMap API key and try again."
                    if response.status_code == 401:
                        error_detail = "Authentication failed. Invalid OpenWeatherMap API key."
                    elif response.status_code == 429:
                        error_detail = "Rate limit exceeded. Please check your OpenWeatherMap usage limits."
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_detail
                    )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Request timed out while validating the API key with OpenWeatherMap service. Please try again later."
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to validate API key with OpenWeatherMap service: {str(e)}"
            )

    elif provider == "deepl":
        # Validate the API key format (DeepL keys end with ':fx' for free tier or ':gx' for pro tier)
        if not (api_key.endswith(':fx') or api_key.endswith(':gx')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid API key format. DeepL API keys should end with ':fx' (free) or ':gx' (pro).",
            )

        # Test the API key by making a simple translation request to the DeepL API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api-free.deepl.com/v2/translate" if api_key.endswith(':fx') else "https://api.deepl.com/v2/translate",
                    headers={
                        "Authorization": f"DeepL-Auth-Key {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": ["Hello"],
                        "target_lang": "FR"
                    },
                    timeout=10.0
                )
                if response.status_code != 200:
                    error_detail = "Invalid API key or API error. Please check your DeepL API key and try again."
                    if response.status_code == 403:
                        error_detail = "Authentication failed. Invalid DeepL API key."
                    elif response.status_code == 456:
                        error_detail = "Quota exceeded. Please check your DeepL usage limits."
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_detail
                    )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Request timed out while validating the API key with DeepL service. Please try again later."
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to validate API key with DeepL service: {str(e)}"
            )

    # Check if a connection already exists for this user and service
    existing_connection = get_service_connection_by_user_and_service(db, str(current_user.id), provider)
    if existing_connection:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A service connection for {provider} already exists for this user"
        )
    
    # Encrypt the API key
    encrypted_api_key = encrypt_token(api_key)
    
    # Create a new service connection record
    service_connection = ServiceConnection(
        user_id=current_user.id,
        service_name=provider,
        encrypted_access_token=encrypted_api_key,
        oauth_metadata={"connection_type": "api_key"}  # Mark as API key connection
    )
    
    db.add(service_connection)
    db.commit()
    db.refresh(service_connection)
    
    # Schedule service connection activity log using background task
    background_tasks.add_task(
        log_user_activity_task,
        user_id=str(current_user.id),
        action_type="service_connected",
        details=f"User connected {provider} service using API key",
        service_name=provider.title(),
        status="success"
    )
    
    return {
        "message": f"Successfully added {provider} API key",
        "connection_id": str(service_connection.id),
        "provider": provider,
        "connected_at": service_connection.created_at,
    }


__all__ = ["router"]
