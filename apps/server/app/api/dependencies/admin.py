"""Admin authentication dependencies for API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_active_user
from app.db.session import get_db
from app.models.user import User


def require_admin_user(
    current_user: Annotated[User, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Validate that the current user has admin privileges."""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource.",
        )
    
    return current_user


__all__ = ["require_admin_user"]