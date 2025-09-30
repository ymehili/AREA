"""Admin user service functions for user management dashboard."""

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Tuple
from app.models.user import User
from app.schemas.auth import UserRead


def get_paginated_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    sort: str = "created_at",
    order: str = "desc"
) -> Tuple[List[UserRead], int]:
    """
    Get paginated users with optional search, sorting, and filtering.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Search term to filter users by email
        sort: Field to sort by (default: created_at)
        order: Sort order ('asc' or 'desc', default: desc)
    
    Returns:
        Tuple of (list of users as UserRead objects, total count)
    """
    # Base query
    query = select(User)
    
    # Apply search filter if provided
    if search:
        query = query.where(User.email.contains(search))
    
    # Validate and apply sorting
    valid_sort_fields = {
        "id": User.id,
        "email": User.email,
        "created_at": User.created_at,
        "is_confirmed": User.is_confirmed,
        "is_admin": User.is_admin
    }
    
    sort_column = valid_sort_fields.get(sort, User.created_at)
    
    if order.lower() == "asc":
        query = query.order_by(sort_column)
    else:
        query = query.order_by(sort_column.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar()
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    users = db.execute(query).scalars().all()
    
    # Convert to UserRead schemas
    user_read_list = [UserRead.model_validate(user) for user in users]
    
    return user_read_list, total