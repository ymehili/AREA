"""
Comprehensive tests for OAuth state validation security.

These tests ensure that the OAuth state validation logic properly handles:
- Base64 padding edge cases
- Stateless mode (mobile apps)
- Session-based mode (web apps)
- Malformed state parameters
- CSRF protection
"""

import base64
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status

from app.api.routes.service_connections import decode_oauth_state
from tests.conftest import SyncASGITestClient


class TestOAuthStateDecoding:
    """Test the decode_oauth_state helper function."""

    def test_decode_valid_state_with_padding(self) -> None:
        """Test decoding state that requires base64 padding."""
        # Create state that will need padding (not multiple of 4)
        state_data = {"state": "abc123", "is_mobile": True, "user_id": "test-user-id"}
        state_json = json.dumps(state_data)
        # Encode and strip padding to simulate real-world scenario
        state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode().rstrip('=')

        # Verify it needs padding (not multiple of 4)
        assert len(state_b64) % 4 != 0, "Test setup: state should need padding"

        # Decode should work despite missing padding
        state_base, is_mobile, user_id = decode_oauth_state(state_b64)

        assert state_base == "abc123"
        assert is_mobile is True
        assert user_id == "test-user-id"

    def test_decode_valid_state_without_padding(self) -> None:
        """Test decoding state that doesn't need base64 padding."""
        state_data = {"state": "x" * 16, "is_mobile": False, "user_id": "test-id"}
        state_json = json.dumps(state_data)
        state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()

        state_base, is_mobile, user_id = decode_oauth_state(state_b64)

        assert state_base == "x" * 16
        assert is_mobile is False
        assert user_id == "test-id"

    def test_decode_state_missing_user_id(self) -> None:
        """Test decoding state without user_id (web flow)."""
        state_data = {"state": "web-state-123", "is_mobile": False}
        state_json = json.dumps(state_data)
        state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()

        state_base, is_mobile, user_id = decode_oauth_state(state_b64)

        assert state_base == "web-state-123"
        assert is_mobile is False
        assert user_id is None

    def test_decode_malformed_base64(self) -> None:
        """Test decoding invalid base64 returns None values."""
        invalid_state = "not-valid-base64!@#$"

        state_base, is_mobile, user_id = decode_oauth_state(invalid_state)

        assert state_base is None
        assert is_mobile is False
        assert user_id is None

    def test_decode_valid_base64_invalid_json(self) -> None:
        """Test decoding valid base64 but invalid JSON returns None values."""
        invalid_json = "not json at all"
        state_b64 = base64.urlsafe_b64encode(invalid_json.encode()).decode()

        state_base, is_mobile, user_id = decode_oauth_state(state_b64)

        assert state_base is None
        assert is_mobile is False
        assert user_id is None

    def test_decode_empty_state(self) -> None:
        """Test decoding empty state returns None values."""
        state_base, is_mobile, user_id = decode_oauth_state("")

        assert state_base is None
        assert is_mobile is False
        assert user_id is None

    def test_decode_state_with_special_characters(self) -> None:
        """Test decoding state with special characters in user_id."""
        state_data = {
            "state": "state-with-special-chars",
            "is_mobile": True,
            "user_id": "550e8400-e29b-41d4-a716-446655440000"  # UUID format
        }
        state_json = json.dumps(state_data)
        state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()

        state_base, is_mobile, user_id = decode_oauth_state(state_b64)

        assert state_base == "state-with-special-chars"
        assert is_mobile is True
        assert user_id == "550e8400-e29b-41d4-a716-446655440000"


class TestOAuthCallbackStateValidation:
    """Test OAuth callback endpoint state validation."""

    def test_callback_with_invalid_state_no_session(self, client: SyncASGITestClient) -> None:
        """Test callback with invalid state and no session - should fail validation."""
        response = client.get(
            "/api/v1/service-connections/callback/github?code=test_code&state=invalid_state"
        )

        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert "error=invalid_state" in response.headers["location"]

    def test_callback_with_valid_stateless_mode(self, client: SyncASGITestClient, db_session) -> None:
        """Test callback with valid stateless mode (mobile flow with user_id in state)."""
        # Create a valid user
        from app.models.user import User
        from app.core.security import get_password_hash

        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password=get_password_hash("password123"),
            is_confirmed=True
        )
        db_session.add(user)
        db_session.commit()

        # Create valid state with user_id (stateless/mobile mode)
        state_data = {
            "state": "mobile-state-123",
            "is_mobile": True,
            "user_id": str(user.id)
        }
        state_json = json.dumps(state_data)
        state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()

        # Mock the OAuth callback handler
        with patch('app.api.routes.service_connections.OAuthConnectionService.handle_oauth_callback') as mock_handle:
            from app.models.service_connection import ServiceConnection

            mock_connection = ServiceConnection(
                id=uuid.uuid4(),
                user_id=user.id,
                service_name="github",
                encrypted_access_token="encrypted_token"
            )
            mock_handle.return_value = mock_connection

            response = client.get(
                f"/api/v1/service-connections/callback/github?code=test_code&state={state_b64}"
            )

            # Should succeed with stateless validation
            assert response.status_code == status.HTTP_303_SEE_OTHER
            # Mobile redirect should NOT have /connections path
            assert "success=connected" in response.headers["location"]
            assert "service=github" in response.headers["location"]

            # Verify the callback was called with correct user_id
            # handle_oauth_callback(provider, code, user_id, db)
            mock_handle.assert_called_once()
            call_args = mock_handle.call_args
            # call_args[0] contains positional args: (provider, code, user_id, db)
            assert call_args[0][2] == str(user.id)  # user_id is 3rd positional arg

    def test_callback_with_malformed_state_falls_back(self, client: SyncASGITestClient) -> None:
        """Test callback with malformed state uses fallback and fails validation."""
        malformed_state = "not-valid-base64!@#$"

        response = client.get(
            f"/api/v1/service-connections/callback/github?code=test_code&state={malformed_state}"
        )

        # Should fail validation since fallback doesn't match session either
        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert "error=invalid_state" in response.headers["location"]

    def test_callback_oauth_error_with_valid_mobile_state(self, client: SyncASGITestClient) -> None:
        """Test callback OAuth error with valid mobile state redirects to mobile URL."""
        state_data = {
            "state": "error-state",
            "is_mobile": True,
            "user_id": str(uuid.uuid4())
        }
        state_json = json.dumps(state_data)
        state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()

        # Include code parameter even with error to satisfy FastAPI validation
        response = client.get(
            f"/api/v1/service-connections/callback/github?code=dummy&error=access_denied&state={state_b64}"
        )

        # Should redirect to mobile URL (not /connections path)
        assert response.status_code == status.HTTP_303_SEE_OTHER
        location = response.headers["location"]
        assert "/connections" not in location  # Mobile redirect has no /connections
        assert "error=access_denied" in location

    def test_callback_oauth_error_with_web_state(self, client: SyncASGITestClient) -> None:
        """Test callback OAuth error with web state redirects to web URL."""
        state_data = {
            "state": "error-state",
            "is_mobile": False,
            "user_id": None
        }
        state_json = json.dumps(state_data)
        state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()

        # Include code parameter even with error to satisfy FastAPI validation
        response = client.get(
            f"/api/v1/service-connections/callback/github?code=dummy&error=access_denied&state={state_b64}"
        )

        # Should redirect to web URL (with /connections path)
        assert response.status_code == status.HTTP_303_SEE_OTHER
        location = response.headers["location"]
        assert "/connections" in location  # Web redirect has /connections
        assert "error=access_denied" in location

    def test_callback_state_with_padding_edge_case(self, client: SyncASGITestClient, db_session) -> None:
        """Test callback with state that requires base64 padding (critical security test)."""
        from app.models.user import User
        from app.core.security import get_password_hash

        user = User(
            id=uuid.uuid4(),
            email="padding@test.com",
            hashed_password=get_password_hash("password123"),
            is_confirmed=True
        )
        db_session.add(user)
        db_session.commit()

        # Create state with specific length that needs padding
        # Use a short state value to ensure length % 4 != 0
        state_data = {
            "state": "xyz",  # Short value to trigger padding need
            "is_mobile": True,
            "user_id": str(user.id)
        }
        state_json = json.dumps(state_data)
        state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()

        # Strip padding to simulate URL-safe transmission
        state_b64_no_padding = state_b64.rstrip('=')

        # Verify this needs padding
        assert len(state_b64_no_padding) % 4 != 0, "Test requires state that needs padding"

        with patch('app.api.routes.service_connections.OAuthConnectionService.handle_oauth_callback') as mock_handle:
            from app.models.service_connection import ServiceConnection

            mock_connection = ServiceConnection(
                id=uuid.uuid4(),
                user_id=user.id,
                service_name="github",
                encrypted_access_token="encrypted_token"
            )
            mock_handle.return_value = mock_connection

            response = client.get(
                f"/api/v1/service-connections/callback/github?code=test_code&state={state_b64_no_padding}"
            )

            # Should successfully decode and validate despite missing padding
            assert response.status_code == status.HTTP_303_SEE_OTHER
            assert "success=connected" in response.headers["location"]

    def test_callback_exception_still_decodes_state_for_redirect(self, client: SyncASGITestClient, db_session) -> None:
        """Test that exceptions in callback still properly decode state for correct redirect URL."""
        from app.models.user import User
        from app.core.security import get_password_hash

        user = User(
            id=uuid.uuid4(),
            email="exception@test.com",
            hashed_password=get_password_hash("password123"),
            is_confirmed=True
        )
        db_session.add(user)
        db_session.commit()

        # Create mobile state
        state_data = {
            "state": "exception-state",
            "is_mobile": True,
            "user_id": str(user.id)
        }
        state_json = json.dumps(state_data)
        state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()

        # Force an exception in the OAuth handler
        with patch('app.api.routes.service_connections.OAuthConnectionService.handle_oauth_callback') as mock_handle:
            mock_handle.side_effect = Exception("Simulated OAuth error")

            response = client.get(
                f"/api/v1/service-connections/callback/github?code=test_code&state={state_b64}"
            )

            # Should redirect to mobile URL (decoded state correctly in exception handler)
            assert response.status_code == status.HTTP_303_SEE_OTHER
            location = response.headers["location"]
            assert "/connections" not in location  # Mobile redirect
            assert "error=unknown" in location

    def test_callback_state_csrf_protection(self, client: SyncASGITestClient, db_session) -> None:
        """Test that state validation provides CSRF protection."""
        from app.models.user import User
        from app.core.security import get_password_hash

        # Create two different users
        user1 = User(
            id=uuid.uuid4(),
            email="user1@test.com",
            hashed_password=get_password_hash("password123"),
            is_confirmed=True
        )
        user2 = User(
            id=uuid.uuid4(),
            email="user2@test.com",
            hashed_password=get_password_hash("password123"),
            is_confirmed=True
        )
        db_session.add_all([user1, user2])
        db_session.commit()

        # Create state for user1
        state_data = {
            "state": "csrf-test-state",
            "is_mobile": True,
            "user_id": str(user1.id)
        }
        state_json = json.dumps(state_data)
        state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()

        with patch('app.api.routes.service_connections.OAuthConnectionService.handle_oauth_callback') as mock_handle:
            from app.models.service_connection import ServiceConnection

            # Mock returns connection for user1 (correct user)
            mock_connection = ServiceConnection(
                id=uuid.uuid4(),
                user_id=user1.id,
                service_name="github",
                encrypted_access_token="encrypted_token"
            )
            mock_handle.return_value = mock_connection

            response = client.get(
                f"/api/v1/service-connections/callback/github?code=test_code&state={state_b64}"
            )

            # Should succeed with correct user
            assert response.status_code == status.HTTP_303_SEE_OTHER
            assert "success=connected" in response.headers["location"]

            # Verify the callback used the user_id from the state (CSRF protection)
            # handle_oauth_callback(provider, code, user_id, db)
            call_args = mock_handle.call_args
            # call_args[0] contains positional args: (provider, code, user_id, db)
            assert call_args[0][2] == str(user1.id)  # user_id is 3rd positional arg
            # User2's ID should NOT be used
            assert call_args[0][2] != str(user2.id)
