"""Admin-specific API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.api.dependencies.admin import require_admin_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserRead, UserLogin, TokenResponse
from app.api.dependencies.auth import oauth2_scheme
from app.core.security import verify_password
from app.services.users import get_user_by_email
from app.core.security import create_access_token
from app.core.config import settings
from datetime import timedelta

router = APIRouter(prefix="/admin", tags=["admin"])


from app.schemas.auth import UserLogin, TokenResponse
from app.api.dependencies.auth import oauth2_scheme
from app.core.security import verify_password
from app.services.users import get_user_by_email


@router.get("/login", response_model=dict)
async def admin_login_page():
    """Admin login page endpoint."""
    return {"message": "Admin login page"}


@router.post("/login", response_model=TokenResponse)
async def admin_login(
    user_credentials: UserLogin,
    db: Annotated[Session, Depends(get_db)]
):
    """Handle admin-specific authentication - only allows admin users to login."""
    
    user = get_user_by_email(db, user_credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin login only: This login endpoint is restricted to administrators",
        )
    
    if not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address must be confirmed before accessing this resource.",
        )
    
    # Generate token for the admin user
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/dashboard", response_model=dict, dependencies=[Depends(require_admin_user)])
async def admin_dashboard(current_user: Annotated[User, Depends(require_admin_user)]):
    """Admin dashboard - only accessible to admin users."""
    return {"message": f"Welcome to admin dashboard, {current_user.email}"}


@router.get("/users", response_model=list[UserRead], dependencies=[Depends(require_admin_user)])
async def list_all_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin_user)]
):
    """List all users - only accessible to admin users."""
    users = db.query(User).all()
    return users


__all__ = ["router"]