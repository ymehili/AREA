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


def test_get_user_detail_endpoint_with_admin_token(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the get user detail endpoint with admin token."""
    # Create a regular user
    regular_user = User(
        email="detailtest@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(regular_user)
    db_session.commit()

    response = client.get(
        f"/api/v1/admin/users/{regular_user.id}",
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    
    # Verify that the user detail has expected fields
    assert "id" in data
    assert data["id"] == str(regular_user.id)
    assert data["email"] == "detailtest@example.com"
    assert "full_name" in data
    assert "is_confirmed" in data
    assert "is_admin" in data
    assert "is_suspended" in data
    assert "created_at" in data
    assert "confirmed_at" in data
    assert "service_connections" in data
    assert "areas" in data


def test_get_user_detail_endpoint_user_not_found(
    client: SyncASGITestClient,
    admin_token: str,
) -> None:
    """Test the get user detail endpoint with non-existent user."""
    fake_user_id = str(uuid4())
    
    response = client.get(
        f"/api/v1/admin/users/{fake_user_id}",
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_get_user_detail_endpoint_with_regular_user_token(
    client: SyncASGITestClient,
    auth_token: str,
    db_session,
) -> None:
    """Test the get user detail endpoint with regular user token (should fail)."""
    # Create a regular user
    regular_user = User(
        email="test@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(regular_user)
    db_session.commit()

    response = client.get(
        f"/api/v1/admin/users/{regular_user.id}",
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data


def test_confirm_user_email_endpoint_with_admin_token(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the confirm user email endpoint with admin token."""
    # Create a non-confirmed user
    regular_user = User(
        email="unconfirmed@example.com",
        hashed_password="hashed",
        is_confirmed=False,
    )
    db_session.add(regular_user)
    db_session.commit()
    
    # Verify user is not confirmed initially
    assert regular_user.is_confirmed is False

    response = client.post(
        f"/api/v1/admin/users/{regular_user.id}/confirm-email",
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(regular_user.id)
    assert data["email"] == "unconfirmed@example.com"
    assert data["is_confirmed"] is True
    assert "message" in data

    # Verify the user is now confirmed in the database
    db_session.refresh(regular_user)
    assert regular_user.is_confirmed is True


def test_confirm_user_email_endpoint_user_not_found(
    client: SyncASGITestClient,
    admin_token: str,
) -> None:
    """Test the confirm user email endpoint with non-existent user."""
    fake_user_id = str(uuid4())
    
    response = client.post(
        f"/api/v1/admin/users/{fake_user_id}/confirm-email",
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_suspend_user_endpoint_with_admin_token(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the suspend user endpoint with admin token."""
    # Create a user
    regular_user = User(
        email="suspendtest@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(regular_user)
    db_session.commit()
    
    # Verify user is not suspended initially
    assert regular_user.is_suspended is False

    response = client.put(
        f"/api/v1/admin/users/{regular_user.id}/suspend",
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(regular_user.id)
    assert data["email"] == "suspendtest@example.com"
    assert data["is_suspended"] is True
    assert "message" in data

    # Verify the user is now suspended in the database
    db_session.refresh(regular_user)
    assert regular_user.is_suspended is True


def test_suspend_user_endpoint_user_not_found(
    client: SyncASGITestClient,
    admin_token: str,
) -> None:
    """Test the suspend user endpoint with non-existent user."""
    fake_user_id = str(uuid4())
    
    response = client.put(
        f"/api/v1/admin/users/{fake_user_id}/suspend",
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_delete_user_endpoint_with_admin_token(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the delete user endpoint with admin token."""
    # Create a user
    regular_user = User(
        email="deletetest@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(regular_user)
    db_session.commit()
    
    # Verify user exists
    user_id = regular_user.id
    user_check = db_session.get(User, user_id)
    assert user_check is not None

    response = client.delete(
        f"/api/v1/admin/users/{user_id}",
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

    # Verify the user is deleted from the database
    deleted_user = db_session.get(User, user_id)
    assert deleted_user is None


def test_create_user_endpoint_with_admin_token(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the create user endpoint with admin token."""
    # Test successful user creation
    new_user_data = {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "is_admin": False,
        "full_name": "New User"
    }
    
    response = client.post(
        "/api/v1/admin/users",
        json=new_user_data,
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["is_admin"] is False
    assert data["full_name"] == "New User"
    assert data["is_confirmed"] is False  # Assuming user creation requires confirmation
    assert "id" in data
    assert "created_at" in data
    
    # Verify the user was created in the database
    created_user = get_user_by_email(db_session, "newuser@example.com")
    assert created_user is not None
    assert created_user.email == "newuser@example.com"
    assert created_user.is_admin is False
    assert created_user.full_name == "New User"


def test_create_user_endpoint_with_admin_privileges(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the create user endpoint with admin privileges."""
    # Test creating an admin user
    new_user_data = {
        "email": "newadmin@example.com",
        "password": "securepassword123",
        "is_admin": True,
        "full_name": "New Admin"
    }
    
    response = client.post(
        "/api/v1/admin/users",
        json=new_user_data,
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newadmin@example.com"
    assert data["is_admin"] is True
    assert "id" in data
    
    # Verify the admin user was created in the database
    created_user = get_user_by_email(db_session, "newadmin@example.com")
    assert created_user is not None
    assert created_user.is_admin is True


def test_create_user_endpoint_duplicate_email(
    client: SyncASGITestClient,
    admin_token: str,
    db_session,
) -> None:
    """Test the create user endpoint with duplicate email (should fail)."""
    # Create an existing user first
    existing_user = User(
        email="existing@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(existing_user)
    db_session.commit()
    
    # Try to create a user with the same email
    duplicate_user_data = {
        "email": "existing@example.com",
        "password": "differentpassword123",
        "is_admin": False,
        "full_name": "Duplicate User"
    }
    
    response = client.post(
        "/api/v1/admin/users",
        json=duplicate_user_data,
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 409  # Conflict status
    data = response.json()
    assert "detail" in data
    assert "already exists" in data["detail"]


def test_create_user_endpoint_short_password(
    client: SyncASGITestClient,
    admin_token: str,
) -> None:
    """Test the create user endpoint with short password (should fail)."""
    # Try to create a user with a short password
    invalid_user_data = {
        "email": "shortpass@example.com",
        "password": "123",  # Too short
        "is_admin": False,
        "full_name": "Short Password User"
    }
    
    response = client.post(
        "/api/v1/admin/users",
        json=invalid_user_data,
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in str(data).lower() or "validation" in str(data).lower()


def test_create_user_endpoint_with_regular_user_token(
    client: SyncASGITestClient,
    auth_token: str,
) -> None:
    """Test the create user endpoint with regular user token (should fail)."""
    new_user_data = {
        "email": "forbidden@example.com",
        "password": "securepassword123",
        "is_admin": False,
        "full_name": "Forbidden User"
    }
    
    response = client.post(
        "/api/v1/admin/users",
        json=new_user_data,
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 403  # Forbidden
    data = response.json()
    assert "detail" in data


def test_create_user_endpoint_without_token(
    client: SyncASGITestClient,
) -> None:
    """Test the create user endpoint without token (should fail)."""
    new_user_data = {
        "email": "notoken@example.com",
        "password": "securepassword123",
        "is_admin": False,
        "full_name": "No Token User"
    }
    
    response = client.post(
        "/api/v1/admin/users",
        json=new_user_data,
    )
    assert response.status_code == 401  # Unauthorized
    data = response.json()
    assert "detail" in data


def test_delete_user_endpoint_user_not_found(
    client: SyncASGITestClient,
    admin_token: str,
) -> None:
    """Test the delete user endpoint with non-existent user."""
    fake_user_id = str(uuid4())
    
    response = client.delete(
        f"/api/v1/admin/users/{fake_user_id}",
        headers=_auth_headers(admin_token),
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data