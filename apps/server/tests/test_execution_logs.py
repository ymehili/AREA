"""Unit tests for execution log functionality."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.orm import Session

from app.models.area import Area
from app.models.execution_log import ExecutionLog
from app.models.user import User
from app.schemas.execution_log import ExecutionLogCreate
from app.services.areas import create_area
from app.services.execution_logs import (
    create_execution_log,
    get_execution_log_by_id,
    get_execution_logs_by_area,
    get_execution_logs_for_user,
)
from tests.conftest import SyncASGITestClient

if TYPE_CHECKING:
    from app.core.config import Settings


def _create_user(db: Session, email: str = None) -> User:
    from app.core.security import get_password_hash
    import uuid
    email = email if email else f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        hashed_password=get_password_hash("testpass123"),
        is_confirmed=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_area(db: Session, user_id: str, name: str = None) -> Area:
    from app.schemas.area import AreaCreate
    import uuid
    area_name = name if name else f"Test Area {uuid.uuid4().hex[:8]}"
    area_data = AreaCreate(
        name=area_name,
        trigger_service="time",
        trigger_action="every_interval",
        reaction_service="email",
        reaction_action="send",
        trigger_params={"interval_seconds": 30},
        reaction_params={"to": "test@example.com", "subject": "Test", "body": "Test body"}
    )
    return create_area(db, area_data, user_id)


def _create_execution_log(db: Session, area_id: str) -> ExecutionLog:
    execution_log_data = ExecutionLogCreate(
        area_id=uuid.UUID(area_id),
        status="Success",
        output="Execution completed successfully",
        error_message=None,
        step_details={"step1": "completed", "step2": "completed"}
    )
    return create_execution_log(db, execution_log_data)


def test_create_execution_log_success(db_session: Session) -> None:
    """Test creating an execution log successfully."""
    user = _create_user(db_session)
    area = _create_area(db_session, str(user.id))
    
    execution_log = _create_execution_log(db_session, str(area.id))
    
    assert execution_log.area_id == area.id
    assert execution_log.status == "Success"
    assert execution_log.output == "Execution completed successfully"
    assert execution_log.error_message is None
    assert execution_log.step_details == {"step1": "completed", "step2": "completed"}


def test_get_execution_log_by_id_found(db_session: Session) -> None:
    """Test retrieving an execution log by ID when it exists."""
    user = _create_user(db_session)
    area = _create_area(db_session, str(user.id))
    execution_log = _create_execution_log(db_session, str(area.id))
    
    retrieved = get_execution_log_by_id(db_session, str(execution_log.id))
    
    assert retrieved is not None
    assert retrieved.id == execution_log.id
    assert retrieved.area_id == area.id


def test_get_execution_log_by_id_not_found(db_session: Session) -> None:
    """Test retrieving an execution log by ID when it doesn't exist."""
    fake_id = str(uuid.uuid4())
    retrieved = get_execution_log_by_id(db_session, fake_id)
    
    assert retrieved is None


def test_get_execution_logs_by_area(db_session: Session) -> None:
    """Test retrieving all execution logs for a specific area."""
    user = _create_user(db_session)
    area = _create_area(db_session, str(user.id))
    
    # Create multiple execution logs for the same area
    log1 = _create_execution_log(db_session, str(area.id))
    log2 = _create_execution_log(db_session, str(area.id))
    
    logs = get_execution_logs_by_area(db_session, str(area.id))
    
    assert len(logs) == 2
    log_ids = {str(log.id) for log in logs}
    assert str(log1.id) in log_ids
    assert str(log2.id) in log_ids


def test_get_execution_logs_for_user(db_session: Session) -> None:
    """Test retrieving all execution logs for a user's areas."""
    user = _create_user(db_session)
    area1 = _create_area(db_session, str(user.id))
    area2 = _create_area(db_session, str(user.id))
    
    # Create execution logs for both areas
    log1 = _create_execution_log(db_session, str(area1.id))
    log2 = _create_execution_log(db_session, str(area2.id))
    
    # Create an area for another user to ensure it's not included
    other_user = _create_user(db_session)
    other_area = _create_area(db_session, str(other_user.id))
    other_log = _create_execution_log(db_session, str(other_area.id))
    
    logs = get_execution_logs_for_user(db_session, str(user.id))
    
    assert len(logs) == 2
    log_ids = {str(log.id) for log in logs}
    assert str(log1.id) in log_ids
    assert str(log2.id) in log_ids
    assert str(other_log.id) not in log_ids


def test_execution_logs_api_list_user_logs(
    client: SyncASGITestClient,
    auth_token: str,
    db_session: Session,
) -> None:
    """Test the API endpoint to list all execution logs for a user."""
    from app.core.security import create_access_token
    from jose import jwt
    from app.core.config import settings
    
    # Get user ID from the provided token
    payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    user_id = payload["sub"]
    
    # Create areas and execution logs for the user
    area = _create_area(db_session, user_id)
    log1 = _create_execution_log(db_session, str(area.id))
    log2 = _create_execution_log(db_session, str(area.id))
    
    # Create another user's area to ensure it's not included
    other_user = _create_user(db_session)
    other_area = _create_area(db_session, str(other_user.id))
    other_log = _create_execution_log(db_session, str(other_area.id))
    
    # Call the API endpoint
    response = client.get(
        "/api/v1/execution-logs",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 2
    
    log_ids = {log["id"] for log in logs}
    assert str(log1.id) in log_ids
    assert str(log2.id) in log_ids
    assert str(other_log.id) not in log_ids


def test_execution_logs_api_list_area_logs(
    client: SyncASGITestClient,
    auth_token: str,
    db_session: Session,
) -> None:
    """Test the API endpoint to list execution logs for a specific area."""
    from app.core.security import create_access_token
    from jose import jwt
    from app.core.config import settings
    
    # Get user ID from the provided token
    payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    user_id = payload["sub"]
    
    # Create an area for the user
    area = _create_area(db_session, user_id)
    
    # Create execution logs for the area
    log1 = _create_execution_log(db_session, str(area.id))
    log2 = _create_execution_log(db_session, str(area.id))
    
    # Create another area to test isolation
    other_area = _create_area(db_session, user_id)
    other_log = _create_execution_log(db_session, str(other_area.id))
    
    # Call the API endpoint
    response = client.get(
        f"/api/v1/areas/{area.id}/execution-logs",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 2
    
    log_ids = {log["id"] for log in logs}
    assert str(log1.id) in log_ids
    assert str(log2.id) in log_ids
    assert str(other_log.id) not in log_ids


def test_execution_logs_api_get_single_log(
    client: SyncASGITestClient,
    auth_token: str,
    db_session: Session,
) -> None:
    """Test the API endpoint to get a single execution log."""
    from app.core.security import create_access_token
    from jose import jwt
    from app.core.config import settings
    
    # Get user ID from the provided token
    payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    user_id = payload["sub"]
    
    # Create area and execution log for the user
    area = _create_area(db_session, user_id)
    execution_log = _create_execution_log(db_session, str(area.id))
    
    # Call the API endpoint
    response = client.get(
        f"/api/v1/execution-logs/{execution_log.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    log = response.json()
    assert log["id"] == str(execution_log.id)
    assert log["area_id"] == str(execution_log.area_id)
    assert log["status"] == execution_log.status
    assert log["output"] == execution_log.output


def test_execution_logs_api_get_single_log_permission_denied(
    client: SyncASGITestClient,
    auth_token: str,
    db_session: Session,
) -> None:
    """Test that a user can't access execution logs for someone else's area."""
    from app.core.security import create_access_token
    from jose import jwt
    from app.core.config import settings
    
    # Get user ID from the provided token
    payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    user_id = payload["sub"]
    
    # Create area for another user
    other_user = _create_user(db_session)
    other_area = _create_area(db_session, str(other_user.id))
    execution_log = _create_execution_log(db_session, str(other_area.id))
    
    # Try to access the execution log with the original user's token
    response = client.get(
        f"/api/v1/execution-logs/{execution_log.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # Should return 403 Forbidden
    assert response.status_code == 403