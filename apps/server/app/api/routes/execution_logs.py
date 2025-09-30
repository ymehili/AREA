"""ExecutionLogs API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.dependencies import require_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.area import Area
from app.schemas.execution_log import ExecutionLogResponse
from app.services.execution_logs import (
    get_execution_logs_for_user,
    get_execution_logs_by_area,
    get_execution_log_by_id,
)

router = APIRouter(tags=["execution-logs"])


@router.get(
    "/execution-logs",
    response_model=List[ExecutionLogResponse],
    dependencies=[Depends(require_active_user)],
)
def list_user_execution_logs(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> List[ExecutionLogResponse]:
    """List all execution logs for the authenticated user's areas."""
    execution_logs = get_execution_logs_for_user(db, str(current_user.id))
    return [ExecutionLogResponse.model_validate(log) for log in execution_logs]


@router.get(
    "/areas/{area_id}/execution-logs",
    response_model=List[ExecutionLogResponse],
    dependencies=[Depends(require_active_user)],
)
def list_area_execution_logs(
    area_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> List[ExecutionLogResponse]:
    """List all execution logs for a specific area."""
    from uuid import UUID
    # First, verify that the area belongs to the current user
    uuid_area_id = UUID(area_id)
    area = db.query(Area).filter(Area.id == uuid_area_id).first()
    if not area:
        raise HTTPException(
            status_code=404,
            detail="Area not found",
        )
    
    if str(area.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this area's execution logs",
        )
    
    execution_logs = get_execution_logs_by_area(db, str(uuid_area_id))
    return [ExecutionLogResponse.model_validate(log) for log in execution_logs]


@router.get(
    "/execution-logs/{execution_log_id}",
    response_model=ExecutionLogResponse,
    dependencies=[Depends(require_active_user)],
)
def get_execution_log(
    execution_log_id: str,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> ExecutionLogResponse:
    """Get a specific execution log by ID."""
    from uuid import UUID
    uuid_execution_log_id = UUID(execution_log_id)
    execution_log = get_execution_log_by_id(db, str(uuid_execution_log_id))
    if not execution_log:
        raise HTTPException(
            status_code=404,
            detail="Execution log not found",
        )
    
    # Check if the execution log belongs to an area that belongs to the current user
    if str(execution_log.area.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this execution log",
        )
    
    return ExecutionLogResponse.model_validate(execution_log)


__all__ = ["router"]