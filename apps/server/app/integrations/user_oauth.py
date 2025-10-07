"""OAuth service integration for third-party authentication."""

from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services.users import get_user_by_email, create_user
from app.services.user_activity_logs import create_user_activity_log, log_user_activity_task
from app.schemas.user_activity_log import UserActivityLogCreate


class OAuthService:
    """Service for handling OAuth authentication flows."""
    
    _oauth_client: Optional[OAuth] = None
    
    @classmethod
    def _get_oauth_client(cls) -> OAuth:
        """Get or create OAuth client instance. Factory method for testability."""
        if cls._oauth_client is None:
            cls._oauth_client = cls._create_oauth_client()
        return cls._oauth_client
    
    @classmethod
    def _create_oauth_client(cls) -> OAuth:
        """Create and configure OAuth client."""
        oauth = OAuth()
        
        # Register Google OAuth provider only if configured
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
        
        return oauth
    
    @classmethod
    def _reset_oauth_client(cls) -> None:
        """Reset OAuth client. Used for testing."""
        cls._oauth_client = None
    
    @staticmethod
    def is_oauth_configured() -> bool:
        """Check if OAuth is properly configured."""
        return bool(settings.google_client_id and settings.google_client_secret)
    
    @classmethod
    async def get_google_authorization_url(cls, request: Request) -> RedirectResponse:
        """Get Google OAuth authorization URL and redirect response."""
        if not cls.is_oauth_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth is not properly configured"
            )
        
        try:
            oauth = cls._get_oauth_client()
            redirect_uri = f"{settings.oauth_redirect_base_url}/google/callback"
            return await oauth.google.authorize_redirect(request, redirect_uri)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initiate OAuth: {str(e)}"
            )
    
    @classmethod
    async def handle_google_callback(cls, request: Request, db: Session) -> TokenResponse:
        """Handle Google OAuth callback and create/access user."""
        if not cls.is_oauth_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth is not properly configured"
            )
        
        try:
            oauth = cls._get_oauth_client()
            
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
            user = cls._find_or_create_google_user(db, email, google_sub)
            
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
                # Create new user by calling the create_user function but using a workaround
                # Since OAuth users don't have passwords, we'll handle this differently
                from app.schemas.auth import UserCreate
                # Temporarily use a mock password - we'll overwrite it after creation
                user_in = UserCreate(
                    email=email,
                    password="oauth_temp_password"  # This will be overwritten with empty string
                    # Note: full_name is not a field in UserCreate schema, so not passing it
                )
                
                # Create the user using the service function
                user = create_user(db, user_in, send_email=False)  # Don't send confirmation email for OAuth users
                
                # Update the user to set OAuth-specific fields
                user.hashed_password = ""  # Remove password for OAuth users
                user.google_oauth_sub = google_sub
                user.is_confirmed = True  # OAuth users are automatically confirmed
                db.add(user)  # SQLAlchemy needs to track this change
                db.commit()
                db.refresh(user)
        
        # Log successful OAuth login activity in a resilient way
        # Using try-except to ensure the main operation continues even if logging fails
        try:
            activity_log = UserActivityLogCreate(
                user_id=user.id,
                action_type="user_login",
                details=f"User successfully logged in via Google OAuth",
                service_name="Google OAuth",
                status="success"
            )
            create_user_activity_log(db, activity_log)
        except Exception:
            # Log the error but don't raise it to prevent breaking the main operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log OAuth login activity for user {user.id}", exc_info=True)
            # In a production setting, this could be added to a message queue for retry
        
        return user
    
    @staticmethod
    def generate_redirect_url(access_token: str, user_agent: str) -> str:
        """Generate appropriate redirect URL based on client type."""
        user_agent_lower = user_agent.lower()
        
        # For mobile apps, use query parameter
        if "mobile" in user_agent_lower or "android" in user_agent_lower or "iphone" in user_agent_lower:
            parsed_mobile_url = urlparse(settings.frontend_redirect_url_mobile)
            mobile_path = parsed_mobile_url.path

            if not mobile_path or mobile_path == "/":
                mobile_path = "/oauth/callback"

            query_params = dict(parse_qsl(parsed_mobile_url.query, keep_blank_values=True))
            query_params["access_token"] = access_token

            mobile_redirect_url = urlunparse(
                parsed_mobile_url._replace(
                    path=mobile_path,
                    query=urlencode(query_params)
                )
            )

            print("Mobile detected")
            print(f"Redirecting to {mobile_redirect_url}")
            return mobile_redirect_url
        
        # For web apps, use URL hash
        print("Not mobile detected")
        return f"{settings.frontend_redirect_url_web}#access_token={access_token}"


__all__ = ["OAuthService"]
