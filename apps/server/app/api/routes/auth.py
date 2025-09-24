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
            detail="Invalid email or password.",
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


__all__ = ["router"]
