"""Authentication dependencies for API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _credentials_exception() -> HTTPException:
    """Return a standardised HTTP 401 exception for auth failures."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_active_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Validate a bearer token and return the associated user."""

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise _credentials_exception() from exc

    subject = payload.get("sub")
    if subject is None:
        raise _credentials_exception()

    try:
        user_id = uuid.UUID(str(subject))
    except ValueError as exc:
        raise _credentials_exception() from exc

    user = db.get(User, user_id)
    if user is None:
        raise _credentials_exception()

    if not user.is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address must be confirmed before accessing this resource.",
        )

    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended. Please contact support.",
        )

    return user


def require_admin_user(
    current_user: Annotated[User, Depends(require_active_user)],
) -> User:
    """Check if current user is an admin, otherwise raise 403."""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    
    return current_user


def get_optional_user(
    db: Annotated[Session, Depends(get_db)],
    token: str | None = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)),
) -> User | None:
    """
    Optionally validate a bearer token and return the associated user.
    Returns None if no token is provided or if token is invalid.
    """
    if token is None:
        return None
    
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None

    subject = payload.get("sub")
    if subject is None:
        return None

    try:
        user_id = uuid.UUID(str(subject))
    except ValueError:
        return None

    user = db.get(User, user_id)
    if user is None:
        return None

    # Don't enforce confirmation or suspension checks for optional auth
    return user


__all__ = ["oauth2_scheme", "require_active_user", "require_admin_user", "get_optional_user"]
