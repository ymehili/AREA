"""Admin API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from uuid import UUID
from fastapi import HTTPException

from app.api.dependencies import require_admin_user
from app.models.user import User
from app.db.session import get_db
from app.services.users import get_paginated_users, update_user_admin_status
from app.schemas.user_admin import PaginatedUserList


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
    sort_field: str = Query("created_at", regex="^(id|email|created_at|is_confirmed)$"),
    sort_direction: str = Query("desc", regex="^(asc|desc)$"),
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


@router.put("/users/{user_id}/admin-status")
def update_user_admin_status(
    user_id: UUID,
    is_admin: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Update a user's admin status (admin only)."""
    updated_user = update_user_admin_status(db, user_id=user_id, is_admin=is_admin)
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


__all__ = ["router"]