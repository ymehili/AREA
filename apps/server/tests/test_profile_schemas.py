"""Tests for profile-related schemas."""

from __future__ import annotations

import pytest

from pydantic import ValidationError

from app.schemas.profile import (
    LoginMethodLinkRequest,
    LoginMethodStatus,
    PasswordChangeRequest,
    UserProfileResponse,
    UserProfileUpdate,
)


def test_user_profile_response_contains_login_methods() -> None:
    response = UserProfileResponse(
        email="user@example.com",
        full_name="Example User",
        is_confirmed=True,
        is_admin=False,
        has_password=True,
        login_methods=[
            LoginMethodStatus(provider="google", linked=True, identifier="google-123"),
            LoginMethodStatus(provider="github", linked=False),
            LoginMethodStatus(provider="microsoft", linked=False),
        ],
    )

    assert response.email == "user@example.com"
    assert response.login_methods[1].linked is False
    assert response.login_methods[1].identifier is None


def test_user_profile_update_strips_whitespace() -> None:
    payload = UserProfileUpdate(full_name=" Example ", email=" person@example.com ")

    assert payload.full_name == "Example"
    assert payload.email == "person@example.com"


def test_password_change_request_enforces_min_length() -> None:
    PasswordChangeRequest(current_password="currentpass", new_password="newpassword")
    with pytest.raises(ValidationError):
        PasswordChangeRequest(current_password="short", new_password="1234567")


def test_login_method_link_request_strips_whitespace() -> None:
    request = LoginMethodLinkRequest(identifier=" external-id ")

    assert request.identifier == "external-id"
