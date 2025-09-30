"""Tests for admin functionality."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.users import grant_admin_privileges, create_user
from app.schemas.auth import UserCreate


def test_admin_user_creation(client: TestClient, db_session: Session):
    """Test that admin privileges can be granted to a user."""
    # Create a regular user first
    user_in = UserCreate(email="regular@example.com", password="testpassword")
    regular_user = create_user(db_session, user_in, send_email=False)
    
    # Grant admin privileges
    admin_user = grant_admin_privileges(db_session, regular_user)
    
    # Verify the user is now an admin
    assert admin_user.is_admin is True


def test_admin_route_requires_authentication(client: TestClient):
    """Test that admin routes require authentication."""
    response = client.get("/admin/dashboard")
    # Should return 401 or 403 if not authenticated
    assert response.status_code in [401, 403]


def test_admin_route_accessible_to_admins(client: TestClient, admin_user: User):
    """Test that admin routes are accessible to admin users."""
    # Log in as admin user
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "testpassword"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Access admin route with token
    response = client.get(
        "/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_non_admin_user_cannot_access_admin_routes(
    client: TestClient, 
    db_session: Session
):
    """Test that non-admin users cannot access admin routes."""
    # Create a regular user first
    user_in = UserCreate(email="regular@example.com", password="testpassword")
    regular_user = create_user(db_session, user_in, send_email=False)
    
    # Log in as regular user
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": regular_user.email, "password": "testpassword"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Try to access admin route with regular user token
    response = client.get(
        "/admin/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    # Should return 403 Forbidden
    assert response.status_code == 403


@pytest.fixture
def admin_user(client: TestClient, db_session: Session) -> User:
    """Create an admin user for testing."""
    # Create a regular user first
    user_in = UserCreate(email="admin@example.com", password="testpassword")
    regular_user = create_user(db_session, user_in, send_email=False)
    admin = grant_admin_privileges(db_session, regular_user)
    return admin