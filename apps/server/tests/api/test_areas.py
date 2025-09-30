"""API tests for area endpoints with multi-step workflows."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


def test_create_area_returns_steps(client: TestClient, db_session: Session, auth_headers: dict):
    """Test that creating an area returns the steps in the response."""
    response = client.post(
        "/api/v1/areas",
        json={
            "name": "Test Multi-Step Area",
            "steps": [
                {
                    "position": 0,
                    "step_type": "action",
                    "service_slug": "time",
                    "action_key": "every_interval",
                    "config": {"interval_seconds": 60},
                },
                {
                    "position": 1,
                    "step_type": "reaction",
                    "service_slug": "debug",
                    "action_key": "log",
                    "config": {"message": "Hello"},
                },
            ],
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["name"] == "Test Multi-Step Area"
    assert data["enabled"] is True
    assert "steps" in data
    assert len(data["steps"]) == 2

    # Verify first step (ACTION)
    assert data["steps"][0]["position"] == 0
    assert data["steps"][0]["step_type"] == "action"
    assert data["steps"][0]["service_slug"] == "time"
    assert data["steps"][0]["action_key"] == "every_interval"
    assert data["steps"][0]["config"]["interval_seconds"] == 60

    # Verify second step (REACTION)
    assert data["steps"][1]["position"] == 1
    assert data["steps"][1]["step_type"] == "reaction"
    assert data["steps"][1]["service_slug"] == "debug"
    assert data["steps"][1]["action_key"] == "log"


def test_create_area_with_delay_step(client: TestClient, auth_headers: dict):
    """Test creating an area with a delay step."""
    response = client.post(
        "/api/v1/areas",
        json={
            "name": "Area with Delay",
            "steps": [
                {
                    "position": 0,
                    "step_type": "action",
                    "service_slug": "time",
                    "action_key": "every_interval",
                    "config": {},
                },
                {
                    "position": 1,
                    "step_type": "delay",
                    "config": {"seconds": 30},
                },
                {
                    "position": 2,
                    "step_type": "reaction",
                    "service_slug": "debug",
                    "action_key": "log",
                    "config": {},
                },
            ],
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["steps"]) == 3
    assert data["steps"][1]["step_type"] == "delay"
    assert data["steps"][1]["service_slug"] is None
    assert data["steps"][1]["action_key"] is None


def test_create_area_validation_first_step_must_be_action(client: TestClient, auth_headers: dict):
    """Test that first step must be an ACTION."""
    response = client.post(
        "/api/v1/areas",
        json={
            "name": "Invalid Area",
            "steps": [
                {
                    "position": 0,
                    "step_type": "reaction",  # Should be action
                    "service_slug": "debug",
                    "action_key": "log",
                    "config": {},
                },
            ],
        },
        headers=auth_headers,
    )

    assert response.status_code == 422  # Validation error


def test_create_area_validation_empty_steps(client: TestClient, auth_headers: dict):
    """Test that at least one step is required."""
    response = client.post(
        "/api/v1/areas",
        json={
            "name": "Invalid Area",
            "steps": [],
        },
        headers=auth_headers,
    )

    assert response.status_code == 422  # Validation error


def test_create_area_validation_action_requires_service_and_key(client: TestClient, auth_headers: dict):
    """Test that ACTION/REACTION steps require service_slug and action_key."""
    response = client.post(
        "/api/v1/areas",
        json={
            "name": "Invalid Area",
            "steps": [
                {
                    "position": 0,
                    "step_type": "action",
                    # Missing service_slug and action_key
                    "config": {},
                },
            ],
        },
        headers=auth_headers,
    )

    assert response.status_code == 422  # Validation error


def test_list_areas_returns_steps(client: TestClient, auth_headers: dict):
    """Test that listing areas returns steps for each area."""
    # Create an area
    client.post(
        "/api/v1/areas",
        json={
            "name": "Test Area",
            "steps": [
                {
                    "position": 0,
                    "step_type": "action",
                    "service_slug": "time",
                    "action_key": "every_interval",
                    "config": {},
                },
            ],
        },
        headers=auth_headers,
    )

    # List areas
    response = client.get("/api/v1/areas", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) > 0
    assert "steps" in data[0]
    assert len(data[0]["steps"]) > 0


def test_update_area_name_only(client: TestClient, auth_headers: dict):
    """Test updating only the area name without changing steps."""
    # Create area
    create_response = client.post(
        "/api/v1/areas",
        json={
            "name": "Original Name",
            "steps": [
                {
                    "position": 0,
                    "step_type": "action",
                    "service_slug": "time",
                    "action_key": "every_interval",
                    "config": {},
                },
            ],
        },
        headers=auth_headers,
    )

    area_id = create_response.json()["id"]

    # Update name
    update_response = client.patch(
        f"/api/v1/areas/{area_id}",
        json={"name": "Updated Name"},
        headers=auth_headers,
    )

    assert update_response.status_code == 200
    data = update_response.json()

    assert data["name"] == "Updated Name"
    assert len(data["steps"]) == 1  # Steps unchanged


def test_update_area_steps(client: TestClient, auth_headers: dict):
    """Test updating area steps."""
    # Create area
    create_response = client.post(
        "/api/v1/areas",
        json={
            "name": "Test Area",
            "steps": [
                {
                    "position": 0,
                    "step_type": "action",
                    "service_slug": "time",
                    "action_key": "every_interval",
                    "config": {},
                },
            ],
        },
        headers=auth_headers,
    )

    area_id = create_response.json()["id"]

    # Update with new steps
    update_response = client.patch(
        f"/api/v1/areas/{area_id}",
        json={
            "steps": [
                {
                    "position": 0,
                    "step_type": "action",
                    "service_slug": "time",
                    "action_key": "every_interval",
                    "config": {"interval_seconds": 300},
                },
                {
                    "position": 1,
                    "step_type": "reaction",
                    "service_slug": "debug",
                    "action_key": "log",
                    "config": {},
                },
            ]
        },
        headers=auth_headers,
    )

    assert update_response.status_code == 200
    data = update_response.json()

    assert len(data["steps"]) == 2
    assert data["steps"][0]["config"]["interval_seconds"] == 300


def test_enable_disable_area(client: TestClient, auth_headers: dict):
    """Test enabling and disabling an area."""
    # Create area
    create_response = client.post(
        "/api/v1/areas",
        json={
            "name": "Test Area",
            "steps": [
                {
                    "position": 0,
                    "step_type": "action",
                    "service_slug": "time",
                    "action_key": "every_interval",
                    "config": {},
                },
            ],
        },
        headers=auth_headers,
    )

    area_id = create_response.json()["id"]

    # Disable
    disable_response = client.post(
        f"/api/v1/areas/{area_id}/disable",
        headers=auth_headers,
    )

    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False

    # Enable
    enable_response = client.post(
        f"/api/v1/areas/{area_id}/enable",
        headers=auth_headers,
    )

    assert enable_response.status_code == 200
    assert enable_response.json()["enabled"] is True


def test_delete_area(client: TestClient, auth_headers: dict):
    """Test deleting an area."""
    # Create area
    create_response = client.post(
        "/api/v1/areas",
        json={
            "name": "Test Area",
            "steps": [
                {
                    "position": 0,
                    "step_type": "action",
                    "service_slug": "time",
                    "action_key": "every_interval",
                    "config": {},
                },
            ],
        },
        headers=auth_headers,
    )

    area_id = create_response.json()["id"]

    # Delete
    delete_response = client.delete(
        f"/api/v1/areas/{area_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 200
    assert delete_response.json() is True

    # Verify it's gone (404 on GET)
    get_response = client.get("/api/v1/areas", headers=auth_headers)
    areas = get_response.json()
    assert not any(area["id"] == area_id for area in areas)


def test_create_area_unauthorized(client: TestClient):
    """Test that creating an area requires authentication."""
    response = client.post(
        "/api/v1/areas",
        json={
            "name": "Test Area",
            "steps": [
                {
                    "position": 0,
                    "step_type": "action",
                    "service_slug": "time",
                    "action_key": "every_interval",
                    "config": {},
                },
            ],
        },
    )

    assert response.status_code == 401


def test_update_area_cross_user_forbidden(client: TestClient, db_session: Session):
    """Test that users cannot update other users' areas."""
    # Create two users
    user1 = User(email="user1@example.com", hashed_password="fake_hash", is_active=True)
    user2 = User(email="user2@example.com", hashed_password="fake_hash", is_active=True)
    db_session.add_all([user1, user2])
    db_session.commit()

    # Create area for user1
    from app.services.areas import create_area
    from app.schemas.area import AreaCreate, AreaStepCreate

    area_data = AreaCreate(
        name="User1 Area",
        steps=[
            AreaStepCreate(
                position=0,
                step_type="action",
                service_slug="time",
                action_key="every_interval",
                config={},
            ),
        ],
    )
    area = create_area(db_session, area_data, str(user1.id))

    # Create token for user2
    from app.core.security import create_access_token

    user2_token = create_access_token(str(user2.id))
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    # Try to update user1's area as user2
    response = client.patch(
        f"/api/v1/areas/{area.id}",
        json={"name": "Hacked Name"},
        headers=user2_headers,
    )

    assert response.status_code == 403
