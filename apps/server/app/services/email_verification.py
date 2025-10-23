"""Helpers for email verification token lifecycle."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User


class EmailVerificationError(Exception):
    """Base class for email verification failures."""


class EmailVerificationTokenInvalidError(EmailVerificationError):
    """Raised when a token cannot be matched to a record."""


class EmailVerificationTokenExpiredError(EmailVerificationError):
    """Raised when attempting to confirm with an expired token."""


class EmailVerificationTokenAlreadyUsedError(EmailVerificationError):
    """Raised when attempting to confirm with an already consumed token."""


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _normalize_to_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware in UTC."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def issue_confirmation_token(db: Session, user: User) -> str:
    """Create and persist a new confirmation token for the user.

    Any previously active tokens for the user are marked as consumed to ensure
    only the latest token can be used. The raw token value is returned for
    inclusion in outbound emails.
    """

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=settings.email_confirmation_token_expiry_minutes)

    statement = select(EmailVerificationToken).where(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.consumed_at.is_(None),
    )
    for existing_token in db.execute(statement).scalars():
        existing_token.consumed_at = now

    raw_token = secrets.token_urlsafe(32)
    token_record = EmailVerificationToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=expiry,
    )
    db.add(token_record)
    user.confirmation_sent_at = now
    db.flush()
    return raw_token


def confirm_user_by_token(db: Session, raw_token: str) -> User:
    """Mark a user as confirmed when presenting a valid token."""

    token_hash = _hash_token(raw_token)
    statement = select(EmailVerificationToken).where(
        EmailVerificationToken.token_hash == token_hash,
    )
    token = db.execute(statement).scalar_one_or_none()
    if token is None:
        raise EmailVerificationTokenInvalidError("Invalid confirmation token.")

    now = datetime.now(timezone.utc)

    if token.consumed_at is not None:
        raise EmailVerificationTokenAlreadyUsedError("Confirmation token already used.")

    expires_at_utc = _normalize_to_utc(token.expires_at)
    if expires_at_utc < now:
        token.consumed_at = token.consumed_at or now
        db.flush()
        raise EmailVerificationTokenExpiredError("Confirmation token has expired.")

    user = token.user
    if user is None:
        raise EmailVerificationTokenInvalidError("Token is not associated with a user.")

    token.consumed_at = now
    if not user.is_confirmed:
        user.is_confirmed = True
        user.confirmed_at = now
    db.flush()
    return user


def build_confirmation_link(token: str) -> str:
    """Construct the externally visible confirmation link for a token."""

    base_url = settings.email_confirmation_base_url
    split = urlsplit(base_url)
    query_params = dict(parse_qsl(split.query, keep_blank_values=True))
    query_params["token"] = token
    new_query = urlencode(query_params)
    return urlunsplit(
        (split.scheme, split.netloc, split.path, new_query, split.fragment)
    )


__all__ = [
    "EmailVerificationError",
    "EmailVerificationTokenAlreadyUsedError",
    "EmailVerificationTokenExpiredError",
    "EmailVerificationTokenInvalidError",
    "build_confirmation_link",
    "confirm_user_by_token",
    "issue_confirmation_token",
]
