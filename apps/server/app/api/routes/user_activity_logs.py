"""API routes for user activity logs."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user_activity_log import UserActivityLogResponse
from app.services.user_activity_logs import get_user_activities


router = APIRouter(tags=["user-activities"])


@router.get("/user-activities", response_model=list[UserActivityLogResponse])
def get_user_activities_endpoint(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[UserActivityLogResponse]:
    """Get the current user's activity logs."""
    activities = get_user_activities(db, str(current_user.id))
    return [UserActivityLogResponse.model_validate(activity) for activity in activities]


__all__ = ["router"]
