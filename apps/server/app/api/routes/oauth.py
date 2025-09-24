"""OAuth API routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.api.dependencies import get_db
from app.integrations.oauth import OAuthService

router = APIRouter(tags=["oauth"])


@router.get("/{provider}")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login flow."""
    # Validate provider
    if provider != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )
    
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
    
    # Handle redirect logic (web-layer concern)
    user_agent = request.headers.get("user-agent", "")
    redirect_url = OAuthService.generate_redirect_url(
        token_response.access_token,
        user_agent
    )
    
    return RedirectResponse(url=redirect_url)


__all__ = ["router"]