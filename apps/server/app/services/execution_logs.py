"""Repository helpers for interacting with execution log records."""

from __future__ import annotations

import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.execution_log import ExecutionLog
from app.models.area import Area
from app.schemas.execution_log import ExecutionLogCreate


class ExecutionLogNotFoundError(Exception):
    """Raised when attempting to access an execution log that doesn't exist."""

    def __init__(self, execution_log_id: str) -> None:
        super().__init__(f"ExecutionLog with id '{execution_log_id}' not found")
        self.execution_log_id = execution_log_id


def get_execution_log_by_id(db: Session, execution_log_id: str) -> Optional[ExecutionLog]:
    """Fetch an execution log by its ID."""
    uuid_id = uuid.UUID(execution_log_id)
    statement = select(ExecutionLog).where(ExecutionLog.id == uuid_id)
    result = db.execute(statement)
    return result.scalar_one_or_none()


def get_execution_logs_by_area(db: Session, area_id: str) -> List[ExecutionLog]:
    """Fetch all execution logs for a specific area."""
    uuid_area_id = uuid.UUID(area_id)
    statement = select(ExecutionLog).where(ExecutionLog.area_id == uuid_area_id)
    result = db.execute(statement)
    return list(result.scalars().all())


def get_execution_logs_for_user(db: Session, user_id: str) -> List[ExecutionLog]:
    """Fetch all execution logs for a user's areas."""
    uuid_user_id = uuid.UUID(user_id)
    statement = select(ExecutionLog).join(Area).where(Area.user_id == uuid_user_id)
    result = db.execute(statement)
    return list(result.scalars().all())


def create_execution_log(db: Session, execution_log_in: ExecutionLogCreate) -> ExecutionLog:
    """Create a new execution log."""
    execution_log = ExecutionLog(
        area_id=execution_log_in.area_id,
        status=execution_log_in.status,
        output=execution_log_in.output,
        error_message=execution_log_in.error_message,
        step_details=execution_log_in.step_details,
    )

    db.add(execution_log)
    db.commit()
    db.refresh(execution_log)
    return execution_log


__all__ = [
    "ExecutionLogNotFoundError",
    "create_execution_log",
    "get_execution_log_by_id",
    "get_execution_logs_by_area",
    "get_execution_logs_for_user",
]