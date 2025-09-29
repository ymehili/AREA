"""Tests for profile management API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.services import get_user_by_email
from tests.conftest import SyncASGITestClient


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_get_profile_returns_user_data(
    client: SyncASGITestClient,
    auth_token: str,
) -> None:
    response = client.get("/api/v1/users/me", headers=_auth_headers(auth_token))
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["has_password"] is True
    assert len(data["login_methods"]) == 3
    assert all("provider" in item for item in data["login_methods"])


def test_update_profile_changes_full_name(
    client: SyncASGITestClient,
    auth_token: str,
    db_session,
) -> None:
    response = client.request(
        "PATCH",
        "/api/v1/users/me",
        json={"full_name": "Updated Tester"},
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["full_name"] == "Updated Tester"

    user = get_user_by_email(db_session, "user@example.com")
    assert user is not None
    assert user.full_name == "Updated Tester"


def test_update_profile_email_resets_confirmation(
    client: SyncASGITestClient,
    auth_token: str,
    db_session,
    capture_outbound_email,
) -> None:
    user = get_user_by_email(db_session, "user@example.com")
    assert user is not None
    user.is_confirmed = True
    user.confirmed_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.request(
        "PATCH",
        "/api/v1/users/me",
        json={"email": "new-email@example.com"},
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "new-email@example.com"
    assert data["is_confirmed"] is False
    assert data["full_name"] is None
    assert capture_outbound_email
    assert capture_outbound_email[-1]["recipient"] == "new-email@example.com"


def test_update_profile_duplicate_email_returns_400(
    client: SyncASGITestClient,
    auth_token: str,
    db_session,
) -> None:
    other = User(
        email="existing@example.com",
        hashed_password="hashed",
        is_confirmed=True,
    )
    db_session.add(other)
    db_session.commit()

    response = client.request(
        "PATCH",
        "/api/v1/users/me",
        json={"email": "existing@example.com"},
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


def test_change_password_success(
    client: SyncASGITestClient,
    auth_token: str,
    db_session,
) -> None:
    response = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "secret123", "new_password": "newpass456"},
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_password"] is True

    user = get_user_by_email(db_session, "user@example.com")
    assert user is not None
    assert verify_password("newpass456", user.hashed_password)


def test_change_password_rejects_wrong_current(
    client: SyncASGITestClient,
    auth_token: str,
) -> None:
    response = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "wrongpass", "new_password": "newpass456"},
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()


def test_link_login_method_flow(
    client: SyncASGITestClient,
    auth_token: str,
) -> None:
    response = client.post(
        "/api/v1/users/me/login-methods/google",
        json={"identifier": "google-123"},
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "google"
    assert data["linked"] is True

    profile = client.get("/api/v1/users/me", headers=_auth_headers(auth_token)).json()
    google_status = next(item for item in profile["login_methods"] if item["provider"] == "google")
    assert google_status["linked"] is True


def test_link_login_method_duplicate_returns_400(
    client: SyncASGITestClient,
    auth_token: str,
) -> None:
    client.post(
        "/api/v1/users/me/login-methods/google",
        json={"identifier": "google-123"},
        headers=_auth_headers(auth_token),
    )

    second = client.post(
        "/api/v1/users/me/login-methods/google",
        json={"identifier": "google-123"},
        headers=_auth_headers(auth_token),
    )
    assert second.status_code == 400


def test_unlink_login_method_flow(
    client: SyncASGITestClient,
    auth_token: str,
) -> None:
    client.post(
        "/api/v1/users/me/login-methods/github",
        json={"identifier": "octocat"},
        headers=_auth_headers(auth_token),
    )

    response = client.request(
        "DELETE",
        "/api/v1/users/me/login-methods/github",
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["linked"] is False

    second = client.request(
        "DELETE",
        "/api/v1/users/me/login-methods/github",
        headers=_auth_headers(auth_token),
    )
    assert second.status_code == 400


def test_unlink_login_method_requires_alternate_auth(
    client: SyncASGITestClient,
    db_session,
) -> None:
    user = User(
        email="oauth-only@example.com",
        hashed_password="",
        google_oauth_sub="oauth-id",
        is_confirmed=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(subject=str(user.id))

    response = client.request(
        "DELETE",
        "/api/v1/users/me/login-methods/google",
        headers=_auth_headers(token),
    )
    assert response.status_code == 400
    assert "remain" in response.json()["detail"].lower()


def test_unsupported_login_provider_returns_404(
    client: SyncASGITestClient,
    auth_token: str,
) -> None:
    response = client.post(
        "/api/v1/users/me/login-methods/twitter",
        json={"identifier": "tw-123"},
        headers=_auth_headers(auth_token),
    )
    assert response.status_code == 404


def test_list_user_service_connections(
    client: SyncASGITestClient,
    auth_token: str,
    db_session: Session,
) -> None:
    """Test the /me/connections endpoint for listing user service connections."""
    import uuid
    from jose import jwt
    from app.models.service_connection import ServiceConnection
    from app.core.config import settings

    # Get user ID from token
    payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    user_id = uuid.UUID(payload["sub"])

    # Create a test service connection
    connection = ServiceConnection(
        id=uuid.uuid4(),
        user_id=user_id,
        service_name="github",
        encrypted_access_token="encrypted_token",
        oauth_metadata={
            "provider": "github",
            "user_info": {"login": "testuser", "id": 123},
            "scopes": ["repo", "user:email"],
            "token_type": "Bearer"
        }
    )
    db_session.add(connection)
    db_session.commit()

    response = client.get(
        "/api/v1/users/me/connections",
        headers=_auth_headers(auth_token),
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Verify the connection data doesn't include sensitive tokens
    connection_data = data[0]
    assert "encrypted_access_token" not in connection_data
    assert "encrypted_refresh_token" not in connection_data
    assert connection_data["service_name"] == "github"
    assert connection_data["oauth_metadata"]["provider"] == "github"


def test_list_user_service_connections_unauthenticated(
    client: SyncASGITestClient,
) -> None:
    """Test the /me/connections endpoint without authentication."""
    response = client.get("/api/v1/users/me/connections")
    assert response.status_code == 401
