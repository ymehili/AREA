"""OAuth service integration for third-party authentication."""

from __future__ import annotations

from typing import Any, Optional, Dict
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services.users import get_user_by_email, create_user
from app.core.security import create_access_token

# Initialize OAuth client
oauth = OAuth()

# Register Google OAuth provider
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile"
        },
        # Explicitly configure the token endpoint
        token_endpoint="https://oauth2.googleapis.com/token",
        # Add timeout to prevent hanging connections
        kwargs={
            "timeout": 30
        }
    )

class OAuthService:
    """Service for handling OAuth authentication flows."""
    
    @staticmethod
    async def get_google_authorization_url(request: Request) -> Dict[str, str]:
        """Get Google OAuth authorization URL."""
        redirect_uri = f"{settings.oauth_redirect_base_url}/google/callback"
        return await oauth.google.authorize_redirect(request, redirect_uri)
    
    @staticmethod
    async def handle_google_callback(request: Request, db: Session) -> TokenResponse:
        """Handle Google OAuth callback and create/access user."""
        try:
            # Get user info from Google
            token = await oauth.google.authorize_access_token(request)
            user_info = token.get("userinfo")
            
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unable to retrieve user information from Google"
                )
            
            email = user_info.get("email")
            google_sub = user_info.get("sub")  # Google's unique user identifier
            
            if not email or not google_sub:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email or Google ID not provided"
                )
            
            # Check if user exists with this Google sub
            user = db.query(User).filter(User.google_oauth_sub == google_sub).first()
            
            # If not found by Google sub, check by email
            if not user:
                user = get_user_by_email(db, email)
                if user and user.google_oauth_sub is None:
                    # Link existing account with Google
                    user.google_oauth_sub = google_sub
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                elif not user:
                    # Create new user
                    from app.schemas.auth import UserCreate
                    user_create = UserCreate(
                        email=email,
                        password=""  # No password for OAuth users
                    )
                    user = create_user(db, user_create)
                    user.google_oauth_sub = google_sub
                    user.is_confirmed = True  # OAuth users are automatically confirmed
                    db.add(user)
                    db.commit()
                    db.refresh(user)
            
            # Create access token
            access_token = create_access_token(subject=str(user.id))
            return TokenResponse(access_token=access_token)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth authentication failed: {str(e)}"
            )

# Create router for OAuth endpoints
router = APIRouter(tags=["oauth"])

@router.get("/{provider}")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login flow."""
    if provider != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )
    
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth is not properly configured"
        )
    
    try:
        redirect_uri = f"{settings.oauth_redirect_base_url}/{provider}/callback"
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth: {str(e)}"
        )

@router.get("/{provider}/callback")
async def oauth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    """Handle OAuth callback and redirect to frontend with JWT token."""
    if provider != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )
    
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth is not properly configured"
        )
    
    try:
        # Get user info from Google
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to retrieve user information from Google"
            )
        
        email = user_info.get("email")
        google_sub = user_info.get("sub")  # Google's unique user identifier
        
        if not email or not google_sub:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or Google ID not provided"
            )
        
        # Check if user exists with this Google sub
        user = db.query(User).filter(User.google_oauth_sub == google_sub).first()
        
        # If not found by Google sub, check by email
        if not user:
            user = get_user_by_email(db, email)
            if user and user.google_oauth_sub is None:
                # Link existing account with Google
                user.google_oauth_sub = google_sub
                db.add(user)
                db.commit()
                db.refresh(user)
            elif not user:
                # Create new user
                from app.schemas.auth import UserCreate
                # Create a temporary password for OAuth users
                user_create = UserCreate(
                    email=email,
                    password="oauth_user_no_password"  # Placeholder password
                )
                user = create_user(db, user_create)
                user.google_oauth_sub = google_sub
                user.is_confirmed = True  # OAuth users are automatically confirmed
                user.hashed_password = ""  # Clear password for OAuth users
                db.add(user)
                db.commit()
                db.refresh(user)
        
        # Create access token
        access_token = create_access_token(subject=str(user.id))
        
        # For mobile apps, redirect to a special page that can handle the token
        # For web apps, redirect with token in URL hash
        user_agent = request.headers.get("user-agent", "").lower()
        if "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent:
            # Mobile app - redirect to a page that can handle the token
            redirect_url = f"{settings.frontend_redirect_url}/oauth/callback?access_token={access_token}"
        else:
            # Web app - redirect with token in URL hash
            redirect_url = f"{settings.frontend_redirect_url}#access_token={access_token}"
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        # Log the full exception for debugging
        import traceback
        print(f"OAuth authentication error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )

__all__ = ["OAuthService", "router"]