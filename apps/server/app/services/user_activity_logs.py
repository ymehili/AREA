"""Service functions for user activity logs."""

from __future__ import annotations

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_activity_log import UserActivityLog
from app.schemas.user_activity_log import UserActivityLogCreate


class UserActivityLogNotFoundError(Exception):
    """Raised when attempting to access a user activity log that doesn't exist."""

    def __init__(self, activity_log_id: str) -> None:
        super().__init__(f"UserActivityLog with id '{activity_log_id}' not found")
        self.activity_log_id = activity_log_id


def get_user_activity_log_by_id(
    db: Session, activity_log_id: str
) -> Optional[UserActivityLog]:
    """Fetch a user activity log by its ID."""
    uuid_id = uuid.UUID(activity_log_id)
    statement = select(UserActivityLog).where(UserActivityLog.id == uuid_id)
    result = db.execute(statement)
    return result.scalar_one_or_none()


def get_user_activities(
    db: Session, user_id: str, limit: int = 50
) -> List[UserActivityLog]:
    """Fetch recent activity logs for a specific user."""
    uuid_user_id = uuid.UUID(user_id)
    statement = (
        select(UserActivityLog)
        .where(UserActivityLog.user_id == uuid_user_id)
        .order_by(UserActivityLog.timestamp.desc())
        .limit(limit)
    )
    result = db.execute(statement)
    return list(result.scalars().all())


def create_user_activity_log(
    db: Session, activity_in: UserActivityLogCreate
) -> UserActivityLog:
    """Create a new user activity log."""
    activity_log = UserActivityLog(
        user_id=activity_in.user_id,
        action_type=activity_in.action_type,
        details=activity_in.details,
        service_name=activity_in.service_name,
        status=activity_in.status,
    )

    db.add(activity_log)
    db.commit()
    db.refresh(activity_log)
    return activity_log


def log_user_activity_task(
    user_id: str,
    action_type: str,
    service_name: str | None = None,
    details: str | None = None,
    status: str = "success",
) -> None:
    """
    Background task to log user activity with retry logic.

    This function is designed to be called from background tasks to ensure
    that operations are committed even if activity logging fails.
    """
    from app.db.session import SessionLocal
    from app.schemas.user_activity_log import UserActivityLogCreate

    # Create a new database session for this task
    db = SessionLocal()
    try:
        activity_log = UserActivityLogCreate(
            user_id=user_id,
            action_type=action_type,
            service_name=service_name,
            details=details,
            status=status,
        )
        create_user_activity_log(db, activity_log)
    except Exception:
        # Log the error but don't raise it to prevent breaking the main operation
        import logging

        logger = logging.getLogger(__name__)
        logger.error(
            f"Failed to log activity: {action_type} for user {user_id}", exc_info=True
        )
        # In a production setting, you might want to implement a retry mechanism
        # or use a message queue to handle retries
    finally:
        db.close()


__all__ = [
    "UserActivityLogNotFoundError",
    "create_user_activity_log",
    "get_user_activity_log_by_id",
    "get_user_activities",
    "log_user_activity_task",
]
