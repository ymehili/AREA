"""Repository helpers for interacting with user records."""

from __future__ import annotations

from typing import Callable, Optional

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.auth import UserCreate
from app.services.email import send_confirmation_email
from app.services.email_verification import build_confirmation_link, issue_confirmation_token


class UserEmailAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an email that already exists."""

    def __init__(self, email: str) -> None:
        super().__init__(f"A user with email '{email}' already exists")
        self.email = email


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Fetch a user by email address."""

    normalized_email = email.strip().lower()
    statement = select(User).where(User.email == normalized_email)
    result = db.execute(statement)
    return result.scalar_one_or_none()


def create_user(
    db: Session,
    user_in: UserCreate,
    *,
    background_tasks: BackgroundTasks | None = None,
    email_sender: Callable[[str, str], None] | None = None,
) -> User:
    """Create a new user with hashed password handling duplicates gracefully."""

    normalized_email = str(user_in.email).strip().lower()
    existing_user = get_user_by_email(db, normalized_email)
    if existing_user is not None:
        raise UserEmailAlreadyExistsError(normalized_email)

    user = User(
        email=normalized_email,
        hashed_password=get_password_hash(user_in.password),
        is_confirmed=False,
    )

    db.add(user)
    raw_token: str | None = None
    try:
        db.flush()
        raw_token = issue_confirmation_token(db, user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UserEmailAlreadyExistsError(normalized_email) from exc

    db.refresh(user)

    sender = email_sender or send_confirmation_email

    if raw_token and sender is not None:
        confirmation_link = build_confirmation_link(raw_token)
        if background_tasks is not None:
            background_tasks.add_task(sender, user.email, confirmation_link)
        else:
            sender(user.email, confirmation_link)

    return user


__all__ = [
    "UserEmailAlreadyExistsError",
    "create_user",
    "get_user_by_email",
]
