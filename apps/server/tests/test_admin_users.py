"""Test suite for admin user endpoint functionality."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import UserCreate
from app.services.users import create_user, grant_admin_privileges
from app.core.security import create_access_token
from app.core.config import settings
from datetime import timedelta


def test_admin_users_endpoint_requires_admin_auth(
    client: TestClient, 
    db_session: Session
):
    """Test that admin users endpoint requires admin privileges."""
    # Create a regular user first
    user_in = UserCreate(email="regular@example.com", password="testpassword")
    regular_user = create_user(db_session, user_in, send_email=False)
    
    # Create a regular user token (non-admin)
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        subject=str(regular_user.id), expires_delta=access_token_expires
    )
    
    # Try to access admin users endpoint with regular user token
    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should return 403 Forbidden
    assert response.status_code == 403


def test_admin_users_endpoint_with_admin_user(
    client: TestClient, 
    db_session: Session
):
    """Test that admin users endpoint returns paginated users when accessed by admin."""
    # Create an admin user
    user_in = UserCreate(email="admin@example.com", password="testpassword")
    regular_user = create_user(db_session, user_in, send_email=False)
    admin_user = grant_admin_privileges(db_session, regular_user)
    
    # Create an admin user token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        subject=str(admin_user.id), expires_delta=access_token_expires
    )
    
    # Access admin users endpoint with admin user token
    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Should return 200 OK
    assert response.status_code == 200
    
    # Check that response has expected structure
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "pages" in data
    
    # The admin user should be in the list
    assert len(data["items"]) >= 1
    assert data["total"] >= 1


def test_admin_users_endpoint_pagination(
    client: TestClient, 
    db_session: Session
):
    """Test pagination functionality of admin users endpoint."""
    # Create an admin user
    user_in = UserCreate(email="admin@example.com", password="testpassword")
    regular_user = create_user(db_session, user_in, send_email=False)
    admin_user = grant_admin_privileges(db_session, regular_user)
    
    # Create additional users for testing pagination
    for i in range(5):
        user_in = UserCreate(email=f"testuser{i}@example.com", password="testpassword")
        create_user(db_session, user_in, send_email=False)
    
    # Create an admin user token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        subject=str(admin_user.id), expires_delta=access_token_expires
    )
    
    # Test with limit=2 and skip=0
    response = client.get(
        "/api/v1/admin/users",
        params={"limit": 2, "skip": 0},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["items"]) <= 2
    assert data["limit"] == 2
    assert data["page"] == 1


def test_admin_users_endpoint_search(
    client: TestClient, 
    db_session: Session
):
    """Test search functionality of admin users endpoint."""
    # Create an admin user
    user_in = UserCreate(email="searchtest@example.com", password="testpassword")
    regular_user = create_user(db_session, user_in, send_email=False)
    admin_user = grant_admin_privileges(db_session, regular_user)
    
    # Create an admin user token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        subject=str(admin_user.id), expires_delta=access_token_expires
    )
    
    # Search for admin user by email
    response = client.get(
        "/api/v1/admin/users",
        params={"search": admin_user.email},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should find at least the admin user
    assert data["total"] >= 1
    found_admin = any(user["email"] == admin_user.email for user in data["items"])
    assert found_admin


def test_admin_users_endpoint_sorting(
    client: TestClient, 
    db_session: Session
):
    """Test sorting functionality of admin users endpoint."""
    # Create an admin user
    user_in = UserCreate(email="admin@example.com", password="testpassword")
    regular_user = create_user(db_session, user_in, send_email=False)
    admin_user = grant_admin_privileges(db_session, regular_user)
    
    # Create additional users for testing
    for i in range(3):
        user_in = UserCreate(email=f"ztestuser{i}@example.com", password="testpassword")
        create_user(db_session, user_in, send_email=False)
    
    # Create an admin user token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        subject=str(admin_user.id), expires_delta=access_token_expires
    )
    
    # Test sorting by email in ascending order
    response = client.get(
        "/api/v1/admin/users",
        params={"sort": "email", "order": "asc"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # If there are multiple users, check that they are sorted
    if len(data["items"]) > 1:
        emails = [user["email"] for user in data["items"]]
        assert emails == sorted(emails)
    
    # Test sorting by email in descending order
    response_desc = client.get(
        "/api/v1/admin/users",
        params={"sort": "email", "order": "desc"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response_desc.status_code == 200
    data_desc = response_desc.json()
    
    if len(data_desc["items"]) > 1:
        emails_desc = [user["email"] for user in data_desc["items"]]
        assert emails_desc == sorted(emails_desc, reverse=True)