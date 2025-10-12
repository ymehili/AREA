"""Admin API routes."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from uuid import UUID
from fastapi import HTTPException
from typing import Optional
from fastapi import Body

from app.api.dependencies import require_admin_user
from app.models.user import User
from app.db.session import get_db
from app.services.users import (
    get_paginated_users, 
    update_user_admin_status,
    get_user_by_id,
    confirm_user_email_admin,
    suspend_user_account,
    delete_user_account,
    create_user_admin,
    UserEmailAlreadyExistsError
)
from app.schemas.user_admin import PaginatedUserList, UpdateAdminStatusRequest, CreateUserAdminRequest, SuspendUserRequest, DeleteUserRequest
from pydantic import BaseModel, Field
from app.schemas.user_detail_admin import UserDetailAdminResponse
from app.services.admin_audit import create_admin_audit_log


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_user)],
)


@router.get("/users", response_model=PaginatedUserList)
def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str = Query(None),
    sort_field: str = Query("created_at", pattern="^(id|email|created_at|is_confirmed)$"),
    sort_direction: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Get all users with pagination, search, and sorting (admin only)."""
    users, total_count = get_paginated_users(
        db, 
        skip=skip, 
        limit=limit, 
        search=search, 
        sort_field=sort_field, 
        sort_direction=sort_direction
    )
    
    return {
        "users": [
            {
                "id": user.id, 
                "email": user.email, 
                "is_admin": user.is_admin,
                "created_at": user.created_at,
                "is_confirmed": user.is_confirmed
            } for user in users
        ],
        "total_count": total_count,
        "skip": skip,
        "limit": limit
    }


@router.post("/users")
def create_user_admin_endpoint(
    request: CreateUserAdminRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Create a new user via admin panel (admin only)."""
    try:
        user = create_user_admin(
            db,
            email=request.email,
            password=request.password,
            is_admin=request.is_admin,
            full_name=request.full_name,
            send_email=True  # Send confirmation email to new user
        )
        
        return {
            "id": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_confirmed": user.is_confirmed,
            "full_name": user.full_name,  # Include full_name in response
            "created_at": user.created_at, # Include created_at in response
            "message": f"User {user.email} has been created successfully"
        }
    except UserEmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail=f"User with email {request.email} already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the user: {str(e)}")


@router.put("/users/{user_id}/admin-status")
def toggle_admin_status(
    user_id: UUID,
    request: UpdateAdminStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Update a user's admin status (admin only)."""
    updated_user = update_user_admin_status(db, user_id=user_id, is_admin=request.is_admin)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": updated_user.id,
        "email": updated_user.email,
        "is_admin": updated_user.is_admin,
        "message": f"User admin status updated to {'admin' if updated_user.is_admin else 'regular user'}"
    }


@router.get("/status")
def get_admin_status(
    current_user: User = Depends(require_admin_user),
):
    """Get admin panel status."""
    return {
        "status": "ok",
        "admin_user": current_user.email,
        "message": "Admin access confirmed"
    }


@router.get("/users/{user_id}", response_model=UserDetailAdminResponse)
def get_user_detail(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Get detailed information for a specific user (admin only)."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build the response using the schema
    return UserDetailAdminResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_confirmed=user.is_confirmed,
        is_admin=user.is_admin,
        is_suspended=user.is_suspended,
        created_at=user.created_at,
        confirmed_at=user.confirmed_at,
        service_connections=[
            ServiceConnectionForUserDetail(
                id=conn.id,
                service_name=conn.service_name,
                created_at=conn.created_at
            ) for conn in user.service_connections
        ],
        areas=[
            AreaForUserDetail(
                id=area.id,
                name=area.name,
                trigger_service=area.trigger_service,
                reaction_service=area.reaction_service,
                enabled=area.enabled,
                created_at=area.created_at
            ) for area in user.areas
        ]
    )


@router.post("/users/{user_id}/confirm-email")
def confirm_user_email(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Manually confirm a user's email (admin only)."""
    target_user = confirm_user_email_admin(db, current_user, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Log the admin action
    create_admin_audit_log(
        db,
        admin_user_id=current_user.id,
        target_user_id=user_id,
        action_type="confirm_email",
        details=f"Email confirmed by admin {current_user.email}"
    )
    
    return {
        "id": target_user.id,
        "email": target_user.email,
        "is_confirmed": target_user.is_confirmed,
        "message": f"User {target_user.email}'s email has been confirmed"
    }


@router.put("/users/{user_id}/suspend")
def suspend_user(
    user_id: UUID,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Suspend a user account (admin only)."""
    target_user = suspend_user_account(db, current_user, user_id, reason=reason)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": target_user.id,
        "email": target_user.email,
        "is_suspended": target_user.is_suspended,
        "message": f"User {target_user.email}'s account has been suspended"
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: UUID,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Delete a user account (admin only)."""
    success = delete_user_account(db, current_user, user_id, reason=reason)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "message": "User account has been deleted"
    }


__all__ = ["router"]