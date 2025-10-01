"""Tests for admin API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
import pytest
from app.models.user import User
from app.services import get_user_by_email
from tests.conftest import SyncASGITestClient


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_status_endpoint_with_admin_token(
    client: SyncASGITestClient,
    admin_token: str,
) -> None:
    """Test the admin status endpoint with valid admin token."""
    response = client.get("/api/v1/admin/status", headers=_auth_headers(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["admin_user"] == "admin@example.com"
    assert "message" in data


def test_admin_status_endpoint_with_regular_user_token(
    client: SyncASGITestClient,
    auth_token: str,
) -> None:
    """Test the admin status endpoint with regular user token (should fail)."""
    response = client.get("/api/v1/admin/status", headers=_auth_headers(auth_token))
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data


def test_admin_status_endpoint_without_token(
    client: SyncASGITestClient,
) -> None:
    """Test the admin status endpoint without token (should fail)."""
    response = client.get("/api/v1/admin/status")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_get_all_users_endpoint_with_admin_token(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the get all users endpoint with admin token."""
    # Create additional users
    user2 = User(
        email="user2@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    user3 = User(
        email="user3@example.com",
        hashed_password="hashed",
        is_confirmed=False,
    )
    db_session.add(user2)
    db_session.add(user3)
    db_session.commit()

    response = client.get("/api/v1/admin/users", headers=_auth_headers(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total_count" in data
    assert "skip" in data
    assert "limit" in data
    assert data["total_count"] >= 3  # At least the admin user and two others
    assert len(data["users"]) >= 3

    # Verify that users have expected fields
    for user in data["users"]:
        assert "id" in user
        assert "email" in user
        assert "is_admin" in user
        assert "created_at" in user
        assert "is_confirmed" in user


def test_get_all_users_endpoint_with_search(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the get all users endpoint with search parameter."""
    # Create test user
    test_user = User(
        email="searchtest@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(test_user)
    db_session.commit()

    response = client.get(
        "/api/v1/admin/users?search=searchtest", 
        headers=_auth_headers(admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] >= 1
    found_search_user = False
    for user in data["users"]:
        if user["email"] == "searchtest@example.com":
            found_search_user = True
            break
    assert found_search_user


def test_get_all_users_endpoint_with_pagination(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the get all users endpoint with pagination parameters."""
    # Create multiple users
    for i in range(5):
        user = User(
            email=f"pagination{i}@example.com",
            hashed_password="hashed",
            is_confirmed=True,
        )
        db_session.add(user)
    db_session.commit()

    # Test with limit=2
    response = client.get(
        "/api/v1/admin/users?limit=2", 
        headers=_auth_headers(admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 2
    assert len(data["users"]) <= 2


def test_get_all_users_endpoint_with_sorting(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the get all users endpoint with sorting parameters."""
    # Create users with different emails
    user_a = User(
        email="a@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    user_b = User(
        email="b@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(user_a)
    db_session.add(user_b)
    db_session.commit()

    # Test ascending sort by email
    response = client.get(
        "/api/v1/admin/users?sort_field=email&sort_direction=asc", 
        headers=_auth_headers(admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    if len(data["users"]) >= 2:
        # First user should be the one with email starting with 'a'
        assert data["users"][0]["email"] <= data["users"][-1]["email"]


def test_get_all_users_endpoint_with_invalid_sort_params(
    client: SyncASGITestClient,
    admin_token: str,
) -> None:
    """Test the get all users endpoint with invalid sort parameters (should fail)."""
    response = client.get(
        "/api/v1/admin/users?sort_field=invalid_field", 
        headers=_auth_headers(admin_token)
    )
    # This should return 422 due to validation error in the query parameter
    assert response.status_code == 422


def test_get_all_users_endpoint_as_regular_user(
    client: SyncASGITestClient,
    auth_token: str,
) -> None:
    """Test the get all users endpoint with regular user token (should fail)."""
    response = client.get("/api/v1/admin/users", headers=_auth_headers(auth_token))
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data


def test_get_all_users_endpoint_without_token(
    client: SyncASGITestClient,
) -> None:
    """Test the get all users endpoint without token (should fail)."""
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_toggle_admin_status_endpoint_with_admin_token(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the toggle admin status endpoint."""
    # Create a regular user
    regular_user = User(
        email="regular@example.com",
        hashed_password="hashed",
        is_confirmed=True,
        is_admin=False,
    )
    db_session.add(regular_user)
    db_session.commit()

    # Verify user is not admin initially
    assert regular_user.is_admin is False

    # Make the user an admin
    response = client.put(
        f"/api/v1/admin/users/{regular_user.id}/admin-status",
        json={"is_admin": True},
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(regular_user.id)
    assert data["email"] == "regular@example.com"
    assert data["is_admin"] is True
    assert "message" in data

    # Verify the user is now admin in the database
    db_session.refresh(regular_user)
    assert regular_user.is_admin is True

    # Make the user a regular user again
    response = client.put(
        f"/api/v1/admin/users/{regular_user.id}/admin-status",
        json={"is_admin": False},
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(regular_user.id)
    assert data["email"] == "regular@example.com"
    assert data["is_admin"] is False
    assert "message" in data

    # Verify the user is no longer admin in the database
    db_session.refresh(regular_user)
    assert regular_user.is_admin is False


def test_toggle_admin_status_endpoint_user_not_found(
    client: SyncASGITestClient,
    admin_token: str,
) -> None:
    """Test the toggle admin status endpoint with non-existent user."""
    fake_user_id = str(uuid4())
    
    response = client.put(
        f"/api/v1/admin/users/{fake_user_id}/admin-status",
        json={"is_admin": True},
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_toggle_admin_status_endpoint_with_regular_user_token(
    client: SyncASGITestClient,
    auth_token: str,
    db_session,
) -> None:
    """Test the toggle admin status endpoint with regular user token (should fail)."""
    # Create a regular user
    regular_user = User(
        email="test@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(regular_user)
    db_session.commit()

    response = client.put(
        f"/api/v1/admin/users/{regular_user.id}/admin-status",
        json={"is_admin": True},
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data


def test_toggle_admin_status_endpoint_without_token(
    client: SyncASGITestClient,
    db_session,
) -> None:
    """Test the toggle admin status endpoint without token (should fail)."""
    # Create a regular user
    regular_user = User(
        email="test@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(regular_user)
    db_session.commit()

    response = client.put(
        f"/api/v1/admin/users/{regular_user.id}/admin-status",
        json={"is_admin": True},
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_toggle_admin_status_endpoint_invalid_payload(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the toggle admin status endpoint with invalid payload (should fail)."""
    # Create a regular user
    regular_user = User(
        email="test@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(regular_user)
    db_session.commit()

    # Send request with invalid payload (not a boolean)
    response = client.put(
        f"/api/v1/admin/users/{regular_user.id}/admin-status",
        json={"is_admin": "not_a_boolean"},
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 422