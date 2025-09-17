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
from .users import (
    IncorrectPasswordError,
    LastLoginMethodRemovalError,
    LoginProviderAlreadyLinkedError,
    LoginProviderNotLinkedError,
    UserEmailAlreadyExistsError,
    change_user_password,
    create_user,
    get_user_by_email,
    link_login_provider,
    unlink_login_provider,
    update_user_profile,
)

__all__ = [
    "EmailVerificationError",
    "EmailVerificationTokenAlreadyUsedError",
    "EmailVerificationTokenExpiredError",
    "EmailVerificationTokenInvalidError",
    "IncorrectPasswordError",
    "LastLoginMethodRemovalError",
    "LoginProviderAlreadyLinkedError",
    "LoginProviderNotLinkedError",
    "UserEmailAlreadyExistsError",
    "build_confirmation_email",
    "build_confirmation_link",
    "change_user_password",
    "confirm_user_by_token",
    "create_user",
    "get_user_by_email",
    "link_login_provider",
    "issue_confirmation_token",
    "send_confirmation_email",
    "unlink_login_provider",
    "update_user_profile",
]
