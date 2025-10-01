"""Tests for area API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.area import Area
from app.models.area_step import AreaStep
from app.schemas.area import AreaCreate
from app.schemas.area_step import AreaStepCreate
from tests.conftest import SyncASGITestClient


class TestAreaWithStepsEndpoints:
    """Test area endpoints with steps functionality."""

    def test_create_user_area_with_steps_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test creating an area with steps successfully."""
        # Prepare area data with steps
        area_data = {
            "name": "Test Area with Steps",
            "trigger_service": "google_calendar",
            "trigger_action": "new_event",
            "reaction_service": "gmail",
            "reaction_action": "send_email",
            "description": "Test area with steps",
            "is_active": True,
            "steps": [
                {
                    "step_type": "trigger",
                    "order": 0,
                    "service": "google_calendar",
                    "action": "new_event",
                    "config": {"clientId": "step1", "calendarId": "primary"}
                },
                {
                    "step_type": "action",
                    "order": 1,
                    "service": "gmail",
                    "action": "send_email",
                    "config": {
                        "clientId": "step2",
                        "targets": ["step1"],  # Reference to the first step
                        "subject": "New event notification"
                    }
                }
            ]
        }

        response = client.post(
            "/api/v1/areas/with-steps",
            json=area_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Area with Steps"
        assert data["trigger_service"] == "google_calendar"
        assert data["reaction_service"] == "gmail"
        assert len(data["steps"]) == 2
        assert data["steps"][0]["step_type"] == "trigger"
        assert data["steps"][1]["step_type"] == "action"

    def test_create_user_area_with_steps_duplicate_name(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test creating an area with steps when name already exists."""
        # Get user ID from the authenticated user
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an area first
        existing_area = Area(
            user_id=user_id,
            name="Duplicate Area",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test"
        )
        db_session.add(existing_area)
        db_session.commit()

        # Now try to create another area with the same name
        area_data = {
            "name": "Duplicate Area",
            "trigger_service": "test",
            "trigger_action": "test",
            "reaction_service": "test",
            "reaction_action": "test",
            "steps": []
        }

        response = client.post(
            "/api/v1/areas/with-steps",
            json=area_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_user_area_with_steps_unauthenticated(self, client: SyncASGITestClient) -> None:
        """Test creating an area with steps without authentication."""
        area_data = {
            "name": "Test Area with Steps",
            "trigger_service": "google_calendar",
            "trigger_action": "new_event",
            "reaction_service": "gmail",
            "reaction_action": "send_email",
            "steps": []
        }

        response = client.post("/api/v1/areas/with-steps", json=area_data)
        assert response.status_code == 401

    def test_update_user_area_with_steps_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test updating an area with steps successfully."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an area first
        area = Area(
            user_id=user_id,
            name="Original Area",
            trigger_service="original",
            trigger_action="original",
            reaction_service="original",
            reaction_action="original"
        )
        db_session.add(area)
        db_session.commit()

        # Prepare updated area data with steps
        area_data = {
            "name": "Updated Area with Steps",
            "trigger_service": "updated_trigger_service",
            "trigger_action": "updated_trigger_action",
            "reaction_service": "updated_reaction_service",
            "reaction_action": "updated_reaction_action",
            "is_active": True,
            "steps": [
                {
                    "step_type": "trigger",
                    "order": 0,
                    "service": "updated_service",
                    "action": "updated_action",
                    "config": {"clientId": "step1", "param": "value"}
                },
                {
                    "step_type": "action",
                    "order": 1,
                    "service": "another_service",
                    "action": "another_action",
                    "config": {
                        "clientId": "step2",
                        "targets": ["step1"],
                        "param": "value"
                    }
                }
            ]
        }

        response = client.put(
            f"/api/v1/areas/{area.id}/with-steps",
            json=area_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Area with Steps"
        assert data["trigger_service"] == "updated_trigger_service"
        assert data["reaction_service"] == "updated_reaction_service"
        assert len(data["steps"]) == 2
        assert data["steps"][0]["step_type"] == "trigger"
        assert data["steps"][1]["step_type"] == "action"

    def test_update_user_area_with_steps_area_not_found(
        self, client: SyncASGITestClient, auth_token: str
    ) -> None:
        """Test updating an area with steps when area doesn't exist."""
        fake_area_id = str(uuid.uuid4())
        area_data = {
            "name": "Updated Area",
            "trigger_service": "updated_trigger_service",
            "trigger_action": "updated_trigger_action",
            "reaction_service": "updated_reaction_service",
            "reaction_action": "updated_reaction_action",
            "steps": []
        }

        response = client.put(
            f"/api/v1/areas/{fake_area_id}/with-steps",
            json=area_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 404
        assert "Area not found" in response.json()["detail"]

    def test_update_user_area_with_steps_unauthenticated(
        self, client: SyncASGITestClient
    ) -> None:
        """Test updating an area with steps without authentication."""
        fake_area_id = str(uuid.uuid4())
        area_data = {
            "name": "Updated Area",
            "trigger_service": "updated_trigger_service",
            "trigger_action": "updated_trigger_action",
            "reaction_service": "updated_reaction_service",
            "reaction_action": "updated_reaction_action",
            "steps": []
        }

        response = client.put(f"/api/v1/areas/{fake_area_id}/with-steps", json=area_data)
        assert response.status_code == 401

    def test_update_user_area_with_steps_permission_denied(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test updating an area that belongs to another user."""
        # Create an area for a different user
        other_user_id = uuid.uuid4()
        area = Area(
            user_id=other_user_id,
            name="Other User's Area",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test"
        )
        db_session.add(area)
        db_session.commit()

        area_data = {
            "name": "Updated Area",
            "trigger_service": "updated_trigger_service",
            "trigger_action": "updated_trigger_action",
            "reaction_service": "updated_reaction_service",
            "reaction_action": "updated_reaction_action",
            "steps": []
        }

        response = client.put(
            f"/api/v1/areas/{area.id}/with-steps",
            json=area_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 403
        assert "permission" in response.json()["detail"]


class TestAreaEndpoints:
    """Test area endpoints functionality."""

    def test_create_user_area_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test creating an area without steps successfully."""
        area_data = {
            "name": "Test Simple Area",
            "trigger_service": "google_calendar",
            "trigger_action": "new_event",
            "reaction_service": "gmail",
            "reaction_action": "send_email"
        }

        response = client.post(
            "/api/v1/areas",
            json=area_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Simple Area"
        assert data["trigger_service"] == "google_calendar"
        assert data["reaction_service"] == "gmail"

    def test_list_user_areas(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test listing user's areas."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create some test areas
        area1 = Area(
            user_id=user_id,
            name="Area 1",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test"
        )
        area2 = Area(
            user_id=user_id,
            name="Area 2",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test"
        )
        db_session.add_all([area1, area2])
        db_session.commit()

        response = client.get(
            "/api/v1/areas",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        area_names = [area["name"] for area in data]
        assert "Area 1" in area_names
        assert "Area 2" in area_names

    def test_get_area_by_id_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test getting a specific area by ID."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an area with steps
        area = Area(
            user_id=user_id,
            name="Test Area",
            trigger_service="test_service",
            trigger_action="test_action",
            reaction_service="test_reaction_service",
            reaction_action="test_reaction_action"
        )
        db_session.add(area)
        db_session.commit()

        # Create some steps for the area
        step1 = AreaStep(
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="test",
            action="test",
            config={"param": "value"}
        )
        step2 = AreaStep(
            area_id=area.id,
            step_type="action",
            order=1,
            service="test",
            action="test",
            config={"param": "value"}
        )
        db_session.add_all([step1, step2])
        db_session.commit()

        response = client.get(
            f"/api/v1/areas/{str(area.id)}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Area"
        assert data["trigger_service"] == "test_service"
        assert data["reaction_service"] == "test_reaction_service"
        assert len(data["steps"]) == 2

    def test_get_area_by_id_not_found(
        self, client: SyncASGITestClient, auth_token: str
    ) -> None:
        """Test getting an area that doesn't exist."""
        fake_area_id = str(uuid.uuid4())

        response = client.get(
            f"/api/v1/areas/{fake_area_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 404
        assert "Area not found" in response.json()["detail"]

    def test_update_user_area_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test updating an area successfully."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an area
        area = Area(
            user_id=user_id,
            name="Original Area",
            trigger_service="original",
            trigger_action="original",
            reaction_service="original",
            reaction_action="original"
        )
        db_session.add(area)
        db_session.commit()

        # Prepare update data
        area_update_data = {
            "name": "Updated Area",
            "trigger_service": "updated_service",
            "trigger_action": "updated_action",
            "reaction_service": "updated_reaction_service",
            "reaction_action": "updated_reaction_action",
            "enabled": False
        }

        response = client.patch(
            f"/api/v1/areas/{str(area.id)}",
            json=area_update_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Area"
        assert data["trigger_service"] == "updated_service"
        assert data["reaction_service"] == "updated_reaction_service"
        assert data["enabled"] is False

    def test_delete_user_area_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test deleting an area successfully."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an area
        area = Area(
            user_id=user_id,
            name="Area to Delete",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test"
        )
        db_session.add(area)
        db_session.commit()

        response = client.delete(
            f"/api/v1/areas/{str(area.id)}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        assert response.json() is True

        # Verify area was deleted
        response = client.get(
            f"/api/v1/areas/{str(area.id)}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404

    def test_enable_user_area_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test enabling an area."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create a disabled area
        area = Area(
            user_id=user_id,
            name="Disabled Area",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test",
            enabled=False
        )
        db_session.add(area)
        db_session.commit()

        response = client.post(
            f"/api/v1/areas/{str(area.id)}/enable",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True

    def test_disable_user_area_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test disabling an area."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an enabled area
        area = Area(
            user_id=user_id,
            name="Enabled Area",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test",
            enabled=True
        )
        db_session.add(area)
        db_session.commit()

        response = client.post(
            f"/api/v1/areas/{str(area.id)}/disable",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False


class TestAreaStepEndpoints:
    """Test area step endpoints functionality."""

    def test_create_area_step_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test creating an area step successfully."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an area first
        area = Area(
            user_id=user_id,
            name="Area for Steps",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test"
        )
        db_session.add(area)
        db_session.commit()

        # Create step data
        step_data = {
            "area_id": str(area.id),
            "step_type": "action",
            "order": 0,
            "service": "test_service",
            "action": "test_action",
            "config": {"param": "value"}
        }

        response = client.post(
            "/api/v1/areas/steps",
            json=step_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["step_type"] == "action"
        assert data["service"] == "test_service"
        assert data["action"] == "test_action"

    def test_get_area_steps_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test getting all steps for an area."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an area with steps
        area = Area(
            user_id=user_id,
            name="Area with Steps",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test"
        )
        db_session.add(area)
        db_session.commit()

        # Create steps for the area
        step1 = AreaStep(
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="test",
            action="test",
            config={"param": "value1"}
        )
        step2 = AreaStep(
            area_id=area.id,
            step_type="action",
            order=1,
            service="test",
            action="test",
            config={"param": "value2"}
        )
        db_session.add_all([step1, step2])
        db_session.commit()

        response = client.get(
            f"/api/v1/areas/{str(area.id)}/steps",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        step_services = [step["service"] for step in data]
        assert "test" in step_services

    def test_get_area_step_by_id_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test getting a specific step by ID."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an area with a step
        area = Area(
            user_id=user_id,
            name="Area with Step",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test"
        )
        db_session.add(area)
        db_session.commit()

        step = AreaStep(
            area_id=area.id,
            step_type="action",
            order=0,
            service="test_service",
            action="test_action",
            config={"param": "value"}
        )
        db_session.add(step)
        db_session.commit()

        response = client.get(
            f"/api/v1/areas/steps/{str(step.id)}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(step.id)
        assert data["service"] == "test_service"

    def test_update_area_step_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test updating an area step successfully."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an area with a step
        area = Area(
            user_id=user_id,
            name="Area",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test"
        )
        db_session.add(area)
        db_session.commit()

        step = AreaStep(
            area_id=area.id,
            step_type="action",
            order=0,
            service="original_service",
            action="original_action",
            config={"param": "original_value"}
        )
        db_session.add(step)
        db_session.commit()

        # Prepare update data
        step_update_data = {
            "step_type": "trigger",
            "order": 1,
            "service": "updated_service",
            "action": "updated_action",
            "config": {"param": "updated_value"}
        }

        response = client.patch(
            f"/api/v1/areas/steps/{str(step.id)}",
            json=step_update_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "updated_service"
        assert data["action"] == "updated_action"
        assert data["step_type"] == "trigger"

    def test_delete_area_step_success(
        self, client: SyncASGITestClient, auth_token: str, db_session: Session
    ) -> None:
        """Test deleting an area step successfully."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create an area with a step
        area = Area(
            user_id=user_id,
            name="Area",
            trigger_service="test",
            trigger_action="test",
            reaction_service="test",
            reaction_action="test"
        )
        db_session.add(area)
        db_session.commit()

        step = AreaStep(
            area_id=area.id,
            step_type="action",
            order=0,
            service="test_service",
            action="test_action",
            config={"param": "value"}
        )
        db_session.add(step)
        db_session.commit()

        response = client.delete(
            f"/api/v1/areas/steps/{str(step.id)}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        assert response.json() is True

        # Verify step was deleted
        response = client.get(
            f"/api/v1/areas/steps/{str(step.id)}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404