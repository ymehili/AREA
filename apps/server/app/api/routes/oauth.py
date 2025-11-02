"""OAuth API routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.api.dependencies import get_db
from app.integrations.oauth import OAuthService

router = APIRouter(tags=["oauth"])


@router.get("/{provider}")
async def oauth_login(provider: str, request: Request, client_type: str = "web"):
    """Initiate OAuth login flow.

    Args:
        provider: OAuth provider (e.g., 'google')
        client_type: Client type ('web' or 'mobile') - defaults to 'web'
    """
    # Validate provider
    if provider != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )

    # Validate client_type
    if client_type not in ["web", "mobile"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client_type. Must be 'web' or 'mobile'"
        )

    # Store client_type in session for callback
    request.session["client_type"] = client_type

    # Delegate to business logic layer
    return await OAuthService.get_google_authorization_url(request)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle OAuth callback and redirect to frontend with JWT token."""
    # Validate provider
    if provider != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )

    # Get token from business logic layer
    token_response = await OAuthService.handle_google_callback(request, db)

    # Get client_type from session (fallback to user agent detection for backward compatibility)
    client_type = request.session.get("client_type")

    if client_type:
        # Use explicit client_type from session
        redirect_url = OAuthService.generate_redirect_url_by_client_type(
            token_response.access_token,
            client_type
        )
    else:
        # Fallback to user agent detection (for backward compatibility)
        user_agent = request.headers.get("user-agent", "")
        redirect_url = OAuthService.generate_redirect_url(
            token_response.access_token,
            user_agent
        )

    return RedirectResponse(url=redirect_url)


__all__ = ["router"]