"""Repository helpers for interacting with user records."""

from __future__ import annotations

from typing import Callable, Optional

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate
from app.schemas.profile import PasswordChangeRequest, UserProfileUpdate
from app.services.email import send_confirmation_email
from app.services.email_verification import build_confirmation_link, issue_confirmation_token


class UserEmailAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an email that already exists."""

    def __init__(self, email: str) -> None:
        super().__init__(f"A user with email '{email}' already exists")
        self.email = email


class IncorrectPasswordError(Exception):
    """Raised when a provided current password does not match the stored hash."""


class LoginProviderAlreadyLinkedError(Exception):
    """Raised when attempting to link an OAuth provider that is already linked."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"Login provider '{provider}' is already linked.")
        self.provider = provider


class LoginProviderNotLinkedError(Exception):
    """Raised when attempting to unlink a provider that is not currently linked."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"Login provider '{provider}' is not linked.")
        self.provider = provider


class LastLoginMethodRemovalError(Exception):
    """Raised when trying to remove the final login method for an account."""


_PROVIDER_COLUMN_MAP: dict[str, str] = {
    "google": "google_oauth_sub",
    "github": "github_oauth_id",
    "microsoft": "microsoft_oauth_id",
}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _resolve_provider_column(provider: str) -> str:
    try:
        return _PROVIDER_COLUMN_MAP[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported login provider '{provider}'.") from exc


def _has_password(user: User) -> bool:
    return bool(user.hashed_password)


def _has_other_login_methods(user: User, exclude_provider: str | None = None) -> bool:
    for provider, column in _PROVIDER_COLUMN_MAP.items():
        if provider == exclude_provider:
            continue
        if getattr(user, column):
            return True
    return _has_password(user)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Fetch a user by email address."""

    normalized_email = _normalize_email(email)
    statement = select(User).where(User.email == normalized_email)
    result = db.execute(statement)
    return result.scalar_one_or_none()


def create_user(
    db: Session,
    user_in: UserCreate,
    *,
    background_tasks: BackgroundTasks | None = None,
    email_sender: Callable[[str, str], None] | None = None,
    send_email: bool = True,
) -> User:
    """Create a new user with hashed password handling duplicates gracefully."""

    normalized_email = _normalize_email(str(user_in.email))
    existing_user = get_user_by_email(db, normalized_email)
    if existing_user is not None:
        raise UserEmailAlreadyExistsError(normalized_email)

    user = User(
        email=normalized_email,
        hashed_password=get_password_hash(user_in.password),
        is_confirmed=not send_email,
    )

    db.add(user)
    raw_token: str | None = None
    try:
        db.flush()
        if send_email:
            raw_token = issue_confirmation_token(db, user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UserEmailAlreadyExistsError(normalized_email) from exc

    db.refresh(user)

    sender = email_sender or send_confirmation_email

    if send_email and raw_token and sender is not None:
        confirmation_link = build_confirmation_link(raw_token)
        if background_tasks is not None:
            background_tasks.add_task(sender, user.email, confirmation_link)
        else:
            sender(user.email, confirmation_link)

    return user


def update_user_profile(
    db: Session,
    user: User,
    update: UserProfileUpdate,
    *,
    background_tasks: BackgroundTasks | None = None,
    email_sender: Callable[[str, str], None] | None = None,
) -> User:
    """Update mutable profile fields and trigger confirmation on email change."""

    sender = email_sender or send_confirmation_email
    raw_token: str | None = None

    if update.full_name is not None:
        user.full_name = update.full_name or None

    if update.email is not None:
        normalized_email = _normalize_email(str(update.email))
        if normalized_email != user.email:
            existing_user = get_user_by_email(db, normalized_email)
            if existing_user is not None and existing_user.id != user.id:
                raise UserEmailAlreadyExistsError(normalized_email)
            user.email = normalized_email
            user.is_confirmed = False
            user.confirmed_at = None
            raw_token = issue_confirmation_token(db, user)

    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if update.email is not None:
            normalized_email = _normalize_email(str(update.email))
            raise UserEmailAlreadyExistsError(normalized_email) from exc
        raise

    db.refresh(user)

    if raw_token and sender is not None:
        confirmation_link = build_confirmation_link(raw_token)
        if background_tasks is not None:
            background_tasks.add_task(sender, user.email, confirmation_link)
        else:
            sender(user.email, confirmation_link)

    return user


def change_user_password(
    db: Session,
    user: User,
    request: PasswordChangeRequest,
) -> User:
    """Change the user's password after verifying the current one."""

    if not verify_password(request.current_password, user.hashed_password):
        raise IncorrectPasswordError("Current password is incorrect.")
    if len(request.new_password) < 8:
        raise ValueError("New password must be at least 8 characters long.")

    user.hashed_password = get_password_hash(request.new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def link_login_provider(
    db: Session,
    user: User,
    provider: str,
    identifier: str,
) -> User:
    """Link an OAuth provider to the user account."""

    column = _resolve_provider_column(provider)
    if getattr(user, column):
        raise LoginProviderAlreadyLinkedError(provider)

    setattr(user, column, identifier)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def unlink_login_provider(
    db: Session,
    user: User,
    provider: str,
) -> User:
    """Remove a linked OAuth provider ensuring another login method remains."""

    column = _resolve_provider_column(provider)
    if not getattr(user, column):
        raise LoginProviderNotLinkedError(provider)

    if not _has_other_login_methods(user, exclude_provider=provider):
        raise LastLoginMethodRemovalError(provider)

    setattr(user, column, None)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def grant_admin_privileges(db: Session, user: User) -> User:
    """Grant admin privileges to a user."""
    user.is_admin = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


__all__ = [
    "UserEmailAlreadyExistsError",
    "IncorrectPasswordError",
    "LastLoginMethodRemovalError",
    "LoginProviderAlreadyLinkedError",
    "LoginProviderNotLinkedError",
    "create_user",
    "change_user_password",
    "get_user_by_email",
    "grant_admin_privileges",
    "link_login_provider",
    "unlink_login_provider",
    "update_user_profile",
]
