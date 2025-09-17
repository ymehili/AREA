"""Service layer helpers for domain operations."""

from .email import build_confirmation_email, send_confirmation_email
from .email_verification import (
    EmailVerificationError,
    EmailVerificationTokenAlreadyUsedError,
    EmailVerificationTokenExpiredError,
    EmailVerificationTokenInvalidError,
    build_confirmation_link,
    confirm_user_by_token,
    issue_confirmation_token,
)
from .users import UserEmailAlreadyExistsError, create_user, get_user_by_email

__all__ = [
    "EmailVerificationError",
    "EmailVerificationTokenAlreadyUsedError",
    "EmailVerificationTokenExpiredError",
    "EmailVerificationTokenInvalidError",
    "UserEmailAlreadyExistsError",
    "build_confirmation_email",
    "build_confirmation_link",
    "confirm_user_by_token",
    "create_user",
    "get_user_by_email",
    "issue_confirmation_token",
    "send_confirmation_email",
]
