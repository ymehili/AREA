"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.schemas.auth import (
    ResendConfirmationRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.services import (
    EmailVerificationTokenAlreadyUsedError,
    EmailVerificationTokenExpiredError,
    EmailVerificationTokenInvalidError,
    UserEmailAlreadyExistsError,
    build_confirmation_link,
    confirm_user_by_token,
    create_user,
    get_user_by_email,
    issue_confirmation_token,
    send_confirmation_email,
)


router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> UserRead:
    """Register a new user and queue a confirmation email."""

    try:
        user = create_user(
            db,
            payload,
            background_tasks=background_tasks,
        )
    except UserEmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        ) from exc

    return user


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user by email/password and return a JWT token."""

    user = get_user_by_email(db, payload.email)
    if user is None or user.google_oauth_sub is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    if not user.is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address must be confirmed before logging in.",
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.post("/resend-confirmation", status_code=status.HTTP_202_ACCEPTED)
def resend_confirmation_email(
    payload: ResendConfirmationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Issue a new confirmation token and re-send the email."""

    user = get_user_by_email(db, payload.email)
    if user is None:
        # Avoid leaking account existence information.
        return {"message": "If an account exists for this email, a confirmation has been sent."}

    if user.is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already confirmed.",
        )

    raw_token = issue_confirmation_token(db, user)
    db.commit()
    db.refresh(user)

    confirmation_link = build_confirmation_link(raw_token)
    background_tasks.add_task(send_confirmation_email, user.email, confirmation_link)
    return {"message": "Confirmation email resent."}


@router.get("/confirm")
def confirm_email(token: str = Query(...), db: Session = Depends(get_db)) -> RedirectResponse:
    """Validate a confirmation token and redirect to the configured URL."""

    success_url = settings.email_confirmation_success_redirect_url
    failure_url = settings.email_confirmation_failure_redirect_url

    try:
        confirm_user_by_token(db, token)
    except EmailVerificationTokenAlreadyUsedError:
        db.rollback()
        return RedirectResponse(success_url, status_code=status.HTTP_303_SEE_OTHER)
    except EmailVerificationTokenInvalidError:
        db.rollback()
        return RedirectResponse(failure_url, status_code=status.HTTP_303_SEE_OTHER)
    except EmailVerificationTokenExpiredError:
        db.commit()
        return RedirectResponse(failure_url, status_code=status.HTTP_303_SEE_OTHER)
    else:
        db.commit()
        return RedirectResponse(success_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/oauth/{provider}")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login flow."""
    if provider != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )
    
    try:
        from authlib.integrations.starlette_client import OAuth
        oauth = OAuth()
        oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={
                "scope": "openid email profile"
            }
        )
        redirect_uri = f"{settings.oauth_redirect_base_url}/{provider}/callback"
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth: {str(e)}"
        )


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    """Handle OAuth callback and return JWT token."""
    if provider != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )
    
    try:
        from authlib.integrations.starlette_client import OAuth
        from authlib.integrations.httpx_client import AsyncOAuth2Client
        from app.models.user import User
        from app.schemas.auth import UserCreate
        
        oauth = OAuth()
        oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={
                "scope": "openid email profile"
            }
        )
        
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
        return TokenResponse(access_token=access_token)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )


__all__ = ["router"]
