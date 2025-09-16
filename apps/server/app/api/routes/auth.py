"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.security import create_access_token, verify_password
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserRead
from app.services import UserEmailAlreadyExistsError, create_user, get_user_by_email


router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    """Register a new user and return the created record."""

    try:
        user = create_user(db, payload)
    except UserEmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        ) from exc

    return user


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user by email/password and return a JWT token."""

    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


__all__ = ["router"]
