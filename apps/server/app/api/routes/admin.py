"""Admin-specific API routes."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

import uuid
from app.api.dependencies.admin import require_admin_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserRead, UserLogin, TokenResponse, UserCreate
from app.schemas.user_admin import PaginatedUserResponse
from app.services.admin_user_service import get_paginated_users
from app.api.dependencies.auth import oauth2_scheme
from app.core.security import verify_password
from app.services.users import get_user_by_email
from app.core.security import create_access_token, get_password_hash
from app.core.config import settings
from datetime import timedelta

router = APIRouter(prefix="/admin", tags=["admin"])


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


@router.get("/users", response_model=PaginatedUserResponse, dependencies=[Depends(require_admin_user)])
async def list_all_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin_user)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search term to filter users by email"),
    sort: Optional[str] = Query("created_at", description="Field to sort by"),
    order: Optional[str] = Query("desc", description="Sort order: asc or desc")
):
    """List all users with pagination, search, and sorting - only accessible to admin users."""
    users, total = get_paginated_users(db, skip=skip, limit=limit, search=search, sort=sort, order=order)
    
    # Calculate total pages
    pages = (total + limit - 1) // limit
    
    return PaginatedUserResponse(
        items=users,
        total=total,
        page=(skip // limit) + 1,
        limit=limit,
        pages=pages
    )


@router.delete("/users/{user_id}", response_model=dict, dependencies=[Depends(require_admin_user)])
async def delete_user(
    user_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin_user)]
):
    """Delete a user by ID - only accessible to admin users."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot delete their own account"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User with ID {user_id} has been deleted successfully"}


@router.post("/users", response_model=UserRead, dependencies=[Depends(require_admin_user)])
async def create_user(
    user_create: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin_user)],
    is_admin: bool = Query(False, description="Whether to create the user as an admin")
):
    """Create a new user account - only accessible to admin users."""
    from app.services.users import create_user as service_create_user
    from app.core.security import get_password_hash
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_create.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    # Create the user with the provided details
    user = User(
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
        is_confirmed=True,  # Auto-confirm for admin-created users
        is_admin=is_admin
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


__all__ = ["router"]