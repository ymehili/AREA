"""Profile management API routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.dependencies.auth import require_active_user
from app.models.user import User
from app.models.service_connection import ServiceConnection
from app.schemas.profile import (
    LoginMethodLinkRequest,
    LoginMethodStatus,
    PasswordChangeRequest,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.schemas.service_connection import ServiceConnectionRead
from app.services import (
    IncorrectPasswordError,
    LastLoginMethodRemovalError,
    LoginProviderAlreadyLinkedError,
    LoginProviderNotLinkedError,
    UserEmailAlreadyExistsError,
    change_user_password,
    link_login_provider,
    unlink_login_provider,
    update_user_profile,
)

router = APIRouter(tags=["profile"])

_LOGIN_METHOD_COLUMNS: tuple[tuple[str, str], ...] = (
    ("google", "google_oauth_sub"),
    ("github", "github_oauth_id"),
    ("microsoft", "microsoft_oauth_id"),
)


def _build_login_methods(user: User) -> list[LoginMethodStatus]:
    statuses: list[LoginMethodStatus] = []
    for provider, column in _LOGIN_METHOD_COLUMNS:
        identifier = getattr(user, column)
        statuses.append(
            LoginMethodStatus(
                provider=provider,
                linked=bool(identifier),
                identifier=identifier or None,
            )
        )
    return statuses


def _build_profile(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        email=user.email,
        full_name=user.full_name,
        is_confirmed=user.is_confirmed,
        is_admin=user.is_admin,
        has_password=bool(user.hashed_password),
        login_methods=_build_login_methods(user),
    )


def _get_login_method_status(provider: str, user: User) -> LoginMethodStatus:
    for slug, column in _LOGIN_METHOD_COLUMNS:
        if slug == provider:
            identifier = getattr(user, column)
            return LoginMethodStatus(
                provider=slug,
                linked=bool(identifier),
                identifier=identifier or None,
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unsupported login provider '{provider}'.")


@router.get("/me", response_model=UserProfileResponse)
def read_profile(current_user: User = Depends(require_active_user)) -> UserProfileResponse:
    """Return the authenticated user's profile data."""

    return _build_profile(current_user)


@router.patch("/me", response_model=UserProfileResponse)
def update_profile(
    payload: UserProfileUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Update profile attributes for the authenticated user."""

    try:
        updated_user = update_user_profile(
            db,
            current_user,
            payload,
            background_tasks=background_tasks,
        )
    except UserEmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        ) from exc

    return _build_profile(updated_user)


@router.post("/me/password", response_model=UserProfileResponse)
def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Change the authenticated user's password."""

    # WARNING: verify_password() will fail for OAuth users (password = ""). Logic might need adjustment.
    try:
        updated_user = change_user_password(db, current_user, payload)
    except IncorrectPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _build_profile(updated_user)


@router.post("/me/login-methods/{provider}", response_model=LoginMethodStatus)
def link_login_method(
    provider: str,
    payload: LoginMethodLinkRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> LoginMethodStatus:
    """Link an OAuth provider to the authenticated user."""

    try:
        link_login_provider(db, current_user, provider, payload.identifier)
    except LoginProviderAlreadyLinkedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This login method is already linked.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    db.refresh(current_user)
    return _get_login_method_status(provider, current_user)


@router.delete("/me/login-methods/{provider}", response_model=LoginMethodStatus)
def unlink_login_method(
    provider: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> LoginMethodStatus:
    """Unlink an OAuth provider from the authenticated user."""

    try:
        unlink_login_provider(db, current_user, provider)
    except LoginProviderNotLinkedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This login method is not linked.",
        ) from exc
    except LastLoginMethodRemovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one login method must remain linked.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    db.refresh(current_user)
    return _get_login_method_status(provider, current_user)


@router.get("/me/connections", response_model=list[ServiceConnectionRead])
def list_user_service_connections(
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


__all__ = ["router"]
