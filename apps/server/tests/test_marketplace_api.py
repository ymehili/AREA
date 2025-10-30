"""Tests for marketplace API endpoints."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.area import Area
from app.models.marketplace_template import PublishedTemplate
from app.models.user import User
from tests.conftest import SyncASGITestClient


@pytest.fixture()
def test_area(db_session: Session, auth_token: str) -> Area:
    """Create a test area for the authenticated user."""
    from app.services import get_user_by_email
    
    user = get_user_by_email(db_session, "user@example.com")
    
    area = Area(
        user_id=user.id,
        name="Test Workflow for Publishing",
        trigger_service="github",
        trigger_action="new_pr",
        trigger_params={"repo": "test/repo"},
        reaction_service="gmail",
        reaction_action="send_email",
        reaction_params={"to": "test@example.com"},
        enabled=True,
    )
    db_session.add(area)
    db_session.commit()
    db_session.refresh(area)
    return area


@pytest.fixture()
def approved_template(db_session: Session, test_area: Area) -> PublishedTemplate:
    """Create an approved template for testing."""
    from app.services import get_user_by_email
    
    user = get_user_by_email(db_session, "user@example.com")
    
    template = PublishedTemplate(
        original_area_id=test_area.id,
        publisher_user_id=user.id,
        title="Approved Test Template",
        description="This is an approved template for testing public endpoints and cloning functionality.",
        category="productivity",
        template_json={
            "name": test_area.name,
            "trigger": {
                "service": test_area.trigger_service,
                "action": test_area.trigger_action,
                "params": test_area.trigger_params,
                "credential_placeholder": "{{user_credential:github}}",
            },
            "reaction": {
                "service": test_area.reaction_service,
                "action": test_area.reaction_action,
                "params": test_area.reaction_params,
                "credential_placeholder": "{{user_credential:gmail}}",
            },
            "steps": [],
        },
        status="approved",
        visibility="public",
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


def test_list_templates_public(client: SyncASGITestClient, approved_template: PublishedTemplate):
    """Test listing templates without authentication."""
    response = client.get("/api/v1/marketplace/templates")
    
    assert response.status_code == 200
    data = response.json()
    
    # FastAPI pagination response structure
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_list_templates_with_search(client: SyncASGITestClient, approved_template: PublishedTemplate):
    """Test searching templates by keyword."""
    response = client.get("/api/v1/marketplace/templates?q=approved")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should find template with "approved" in title
    assert data["total"] >= 1


def test_list_templates_with_category_filter(client: SyncASGITestClient, approved_template: PublishedTemplate):
    """Test filtering templates by category."""
    response = client.get("/api/v1/marketplace/templates?category=productivity")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] >= 1
    # All results should be productivity category
    for item in data["items"]:
        assert item["category"] == "productivity"


def test_list_templates_with_sorting(client: SyncASGITestClient, approved_template: PublishedTemplate):
    """Test sorting templates."""
    response = client.get("/api/v1/marketplace/templates?sort_by=created_at&order=desc")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data


def test_get_template_detail_public(client: SyncASGITestClient, approved_template: PublishedTemplate):
    """Test getting template details without authentication."""
    response = client.get(f"/api/v1/marketplace/templates/{approved_template.id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == str(approved_template.id)
    assert data["title"] == approved_template.title
    assert data["status"] == "approved"
    assert "template_json" in data


def test_get_template_detail_not_found(client: SyncASGITestClient):
    """Test getting non-existent template returns 404."""
    import uuid
    
    fake_id = uuid.uuid4()
    response = client.get(f"/api/v1/marketplace/templates/{fake_id}")
    
    assert response.status_code == 404


def test_get_template_detail_pending_not_visible(client: SyncASGITestClient, db_session: Session, test_area: Area):
    """Test that pending templates are not visible publicly."""
    from app.services import get_user_by_email
    
    user = get_user_by_email(db_session, "user@example.com")
    
    # Create pending template
    pending_template = PublishedTemplate(
        original_area_id=test_area.id,
        publisher_user_id=user.id,
        title="Pending Template",
        description="This template is pending approval and should not be publicly visible.",
        category="test",
        template_json={"name": "test"},
        status="pending",
        visibility="public",
    )
    db_session.add(pending_template)
    db_session.commit()
    
    # Try to access pending template
    response = client.get(f"/api/v1/marketplace/templates/{pending_template.id}")
    
    assert response.status_code == 404


def test_publish_template_requires_auth(client: SyncASGITestClient, test_area: Area):
    """Test publishing template without authentication returns 401."""
    payload = {
        "area_id": str(test_area.id),
        "title": "Test Template for Auth Check",
        "description": "This request should fail because no authentication token is provided.",
        "category": "test",
        "tags": ["test", "auth"],
    }
    
    response = client.post("/api/v1/marketplace/templates", json=payload)
    
    assert response.status_code == 401


def test_publish_template_success(client: SyncASGITestClient, auth_token: str, test_area: Area):
    """Test successful template publication with authentication."""
    payload = {
        "area_id": str(test_area.id),
        "title": "Successfully Published Template",
        "description": "This template should be successfully published with proper authentication token.",
        "category": "productivity",
        "tags": ["test", "success"],
    }
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/api/v1/marketplace/templates", json=payload, headers=headers)
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["title"] == payload["title"]
    assert data["status"] == "pending"
    assert data["category"] == "productivity"


def test_publish_template_validation_errors(client: SyncASGITestClient, auth_token: str, test_area: Area):
    """Test publishing template with invalid data returns validation errors."""
    payload = {
        "area_id": str(test_area.id),
        "title": "Short",  # Too short (min 10 chars)
        "description": "Too short",  # Too short (min 50 chars)
        "category": "test",
        "tags": ["test"],
    }
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/api/v1/marketplace/templates", json=payload, headers=headers)
    
    assert response.status_code == 422  # Validation error


def test_publish_template_not_owner(client: SyncASGITestClient, auth_token: str, db_session: Session):
    """Test publishing someone else's area returns 403."""
    # Create area owned by different user
    other_user = User(
        email="other@example.com",
        hashed_password="hash",
        is_confirmed=True,
        confirmed_at=datetime.now(),
    )
    db_session.add(other_user)
    db_session.commit()
    
    other_area = Area(
        user_id=other_user.id,
        name="Other User's Workflow",
        trigger_service="github",
        trigger_action="new_pr",
        reaction_service="gmail",
        reaction_action="send_email",
        enabled=True,
    )
    db_session.add(other_area)
    db_session.commit()
    
    payload = {
        "area_id": str(other_area.id),
        "title": "Attempting to Publish Others Work",
        "description": "This should fail because the authenticated user doesn't own this workflow.",
        "category": "test",
        "tags": ["test", "forbidden"],
    }
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post("/api/v1/marketplace/templates", json=payload, headers=headers)
    
    assert response.status_code == 403


def test_clone_template_requires_auth(client: SyncASGITestClient, approved_template: PublishedTemplate):
    """Test cloning template without authentication returns 401."""
    payload = {
        "area_name": "My Cloned Workflow",
        "parameter_overrides": {},
    }
    
    response = client.post(
        f"/api/v1/marketplace/templates/{approved_template.id}/clone",
        json=payload,
    )
    
    assert response.status_code == 401


def test_clone_template_success(client: SyncASGITestClient, auth_token: str, approved_template: PublishedTemplate):
    """Test successful template cloning."""
    payload = {
        "area_name": "My Cloned Automation",
        "parameter_overrides": {},
    }
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post(
        f"/api/v1/marketplace/templates/{approved_template.id}/clone",
        json=payload,
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "created_area_id" in data
    assert "message" in data
    assert "My Cloned Automation" in data["message"]


def test_clone_template_not_found(client: SyncASGITestClient, auth_token: str):
    """Test cloning non-existent template returns 404."""
    import uuid
    
    fake_id = uuid.uuid4()
    payload = {
        "area_name": "Should Fail",
        "parameter_overrides": {},
    }
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post(
        f"/api/v1/marketplace/templates/{fake_id}/clone",
        json=payload,
        headers=headers,
    )
    
    assert response.status_code == 404


def test_approve_template_requires_admin(
    client: SyncASGITestClient,
    auth_token: str,
    db_session: Session,
    test_area: Area,
):
    """Test approving template without admin rights returns 403."""
    from app.services import get_user_by_email
    
    user = get_user_by_email(db_session, "user@example.com")
    
    # Create pending template
    pending = PublishedTemplate(
        original_area_id=test_area.id,
        publisher_user_id=user.id,
        title="Pending for Approval",
        description="This template is waiting for admin approval but requester is not admin.",
        category="test",
        template_json={"name": "test"},
        status="pending",
    )
    db_session.add(pending)
    db_session.commit()
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post(
        f"/api/v1/marketplace/admin/templates/{pending.id}/approve",
        headers=headers,
    )
    
    assert response.status_code == 403


def test_approve_template_success(
    client: SyncASGITestClient,
    admin_token: str,
    db_session: Session,
    test_area: Area,
):
    """Test successful template approval by admin."""
    from app.services import get_user_by_email
    
    user = get_user_by_email(db_session, "user@example.com")
    
    # Create pending template
    pending = PublishedTemplate(
        original_area_id=test_area.id,
        publisher_user_id=user.id,
        title="Ready for Approval",
        description="This template should be successfully approved by an admin user.",
        category="test",
        template_json={"name": "test"},
        status="pending",
    )
    db_session.add(pending)
    db_session.commit()
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post(
        f"/api/v1/marketplace/admin/templates/{pending.id}/approve",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "approved"
    assert "approved_at" in data
    assert "published_at" in data


def test_reject_template_success(
    client: SyncASGITestClient,
    admin_token: str,
    db_session: Session,
    test_area: Area,
):
    """Test successful template rejection by admin."""
    from app.services import get_user_by_email
    
    user = get_user_by_email(db_session, "user@example.com")
    
    # Create pending template
    pending = PublishedTemplate(
        original_area_id=test_area.id,
        publisher_user_id=user.id,
        title="To Be Rejected",
        description="This template will be rejected by admin for quality control reasons.",
        category="test",
        template_json={"name": "test"},
        status="pending",
    )
    db_session.add(pending)
    db_session.commit()
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post(
        f"/api/v1/marketplace/admin/templates/{pending.id}/reject",
        headers=headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "rejected"


def test_get_categories(client: SyncASGITestClient):
    """Test getting template categories."""
    response = client.get("/api/v1/marketplace/categories")
    
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)


def test_get_tags(client: SyncASGITestClient):
    """Test getting popular tags."""
    response = client.get("/api/v1/marketplace/tags")
    
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)


def test_get_tags_with_limit(client: SyncASGITestClient):
    """Test getting tags with custom limit."""
    response = client.get("/api/v1/marketplace/tags?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) <= 10
