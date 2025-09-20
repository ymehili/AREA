"""OAuth service integration for third-party authentication."""

from __future__ import annotations

from typing import Dict
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import TokenResponse, UserCreate
from app.services.users import get_user_by_email, create_user

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
    def is_oauth_configured() -> bool:
        """Check if OAuth is properly configured."""
        return bool(settings.google_client_id and settings.google_client_secret)
    
    @staticmethod
    async def get_google_authorization_url(request: Request) -> any:
        """Get Google OAuth authorization URL and redirect response."""
        if not OAuthService.is_oauth_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth is not properly configured"
            )
        
        try:
            redirect_uri = f"{settings.oauth_redirect_base_url}/google/callback"
            return await oauth.google.authorize_redirect(request, redirect_uri)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initiate OAuth: {str(e)}"
            )
    
    @staticmethod
    async def handle_google_callback(request: Request, db: Session) -> TokenResponse:
        """Handle Google OAuth callback and create/access user."""
        if not OAuthService.is_oauth_configured():
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
            
            # Find or create user
            user = OAuthService._find_or_create_google_user(db, email, google_sub)
            
            # Create access token
            access_token = create_access_token(subject=str(user.id))
            return TokenResponse(access_token=access_token)
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            # Log the full exception for debugging
            import traceback
            print(f"OAuth authentication error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth authentication failed: {str(e)}"
            )
    
    @staticmethod
    def _find_or_create_google_user(db: Session, email: str, google_sub: str) -> User:
        """Find existing user or create new one from Google OAuth data."""
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
                user_create = UserCreate(
                    email=email,
                    password="oauth_user_no_password"  # Placeholder password
                )
                user = create_user(db, user_create, send_email=False)
                user.google_oauth_sub = google_sub
                user.is_confirmed = True  # OAuth users are automatically confirmed
                user.hashed_password = ""  # Clear password for OAuth users
                db.add(user)
                db.commit()
                db.refresh(user)
        
        return user
    
    @staticmethod
    def generate_redirect_url(access_token: str, user_agent: str) -> str:
        """Generate appropriate redirect URL based on client type."""
        user_agent_lower = user_agent.lower()
        
        # For mobile apps, use query parameter
        if "mobile" in user_agent_lower or "android" in user_agent_lower or "iphone" in user_agent_lower:
            return f"{settings.frontend_redirect_url}/oauth/callback?access_token={access_token}"
        
        # For web apps, use URL hash
        return f"{settings.frontend_redirect_url}#access_token={access_token}"


__all__ = ["OAuthService"]