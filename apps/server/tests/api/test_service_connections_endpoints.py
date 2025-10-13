"""Tests for service connections API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock, patch
import pytest
from sqlalchemy.orm import Session

from app.models.service_connection import ServiceConnection
from app.services.service_connections import DuplicateServiceConnectionError
from tests.conftest import SyncASGITestClient


class TestServiceConnectionsEndpoints:
    """Test service connections API endpoints."""

    def test_initiate_service_connection_success(self, client: SyncASGITestClient, auth_token: str) -> None:
        """Test successful OAuth connection initiation."""
        with patch('app.api.routes.service_connections.OAuth2ProviderFactory.get_supported_providers') as mock_get_providers:
            with patch('app.api.routes.service_connections.OAuthConnectionService.generate_oauth_state') as mock_generate_state:
                with patch('app.api.routes.service_connections.OAuthConnectionService.get_authorization_url') as mock_get_url:
                    mock_get_providers.return_value = ["github"]
                    mock_generate_state.return_value = "test_state"
                    mock_get_url.return_value = "https://github.com/login/oauth/authorize?state=test_state"

                    response = client.post(
                        "/api/v1/service-connections/connect/github",
                        headers={"Authorization": f"Bearer {auth_token}"}
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "authorization_url" in data
                    assert "github.com" in data["authorization_url"]

    def test_initiate_service_connection_unsupported_provider(self, client: SyncASGITestClient, auth_token: str) -> None:
        """Test OAuth connection initiation with unsupported provider."""
        with patch('app.api.routes.service_connections.OAuth2ProviderFactory.get_supported_providers') as mock_get_providers:
            mock_get_providers.return_value = []  # No supported providers

            response = client.post(
                "/api/v1/service-connections/connect/github",
                headers={"Authorization": f"Bearer {auth_token}"}
            )

            # The endpoint returns 500 because it catches the exception and logs it
            assert response.status_code == 500

    def test_initiate_service_connection_unauthenticated(self, client: SyncASGITestClient) -> None:
        """Test OAuth connection initiation without authentication."""
        response = client.post("/api/v1/service-connections/connect/github")
        assert response.status_code == 401

    def test_handle_service_connection_callback_invalid_state(self, client: SyncASGITestClient) -> None:
        """Test OAuth callback with invalid state - should redirect with error."""
        response = client.get(
            "/api/v1/service-connections/callback/github?code=test_code&state=invalid_state"
        )

        assert response.status_code == 303  # Redirect
        assert "error=invalid_state" in response.headers["location"]

    def test_handle_service_connection_callback_oauth_error(self, client: SyncASGITestClient) -> None:
        """Test OAuth callback with OAuth error parameter."""
        response = client.get(
            "/api/v1/service-connections/callback/github?error=access_denied"
        )

        assert response.status_code == 422  # Validation error due to missing required state parameter
        assert "detail" in response.json()

    def test_list_user_connections(self, client: SyncASGITestClient, auth_token: str, db_session: Session) -> None:
        """Test listing user connections."""
        # Create a test connection
        connection = ServiceConnection(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            service_name="github",
            encrypted_access_token="encrypted_token",
            oauth_metadata={
                "provider": "github",
                "user_info": {"login": "testuser", "id": 123}
            }
        )
        db_session.add(connection)
        db_session.commit()

        response = client.get(
            "/api/v1/service-connections/connections",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_user_connections_unauthenticated(self, client: SyncASGITestClient) -> None:
        """Test listing connections without authentication."""
        response = client.get("/api/v1/service-connections/connections")
        assert response.status_code == 401

    def test_disconnect_service_success(self, client: SyncASGITestClient, auth_token: str, db_session: Session) -> None:
        """Test successful service disconnection."""
        # We need to get the actual user ID from the auth token
        from jose import jwt
        from app.core.config import settings

        # Decode the token to get user ID
        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create a test connection for the authenticated user
        connection = ServiceConnection(
            id=uuid.uuid4(),
            user_id=user_id,
            service_name="github",
            encrypted_access_token="encrypted_token"
        )
        db_session.add(connection)
        db_session.commit()

        response = client.delete(
            f"/api/v1/service-connections/connections/{connection.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "disconnected successfully" in data["message"]

    def test_disconnect_service_not_found(self, client: SyncASGITestClient, auth_token: str) -> None:
        """Test disconnecting nonexistent service."""
        fake_id = uuid.uuid4()
        response = client.delete(
            f"/api/v1/service-connections/connections/{fake_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_disconnect_service_unauthenticated(self, client: SyncASGITestClient) -> None:
        """Test disconnecting service without authentication."""
        fake_id = uuid.uuid4()
        response = client.delete(f"/api/v1/service-connections/connections/{fake_id}")
        assert response.status_code == 401

    def test_list_oauth_providers(self, client: SyncASGITestClient) -> None:
        """Test listing available OAuth providers."""
        with patch('app.api.routes.service_connections.OAuth2ProviderFactory.get_supported_providers') as mock_get_providers:
            mock_get_providers.return_value = ["github"]

            response = client.get("/api/v1/service-connections/providers")

            assert response.status_code == 200
            data = response.json()
            assert "providers" in data
            assert data["providers"] == ["github"]

    def test_test_provider_api_access_success(self, client: SyncASGITestClient, auth_token: str, db_session: Session) -> None:
        """Test successful provider API access test."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create a test connection
        connection = ServiceConnection(
            id=uuid.uuid4(),
            user_id=user_id,
            service_name="github",
            encrypted_access_token="encrypted_token"
        )
        db_session.add(connection)
        db_session.commit()

        mock_test_result = {"repositories": 5, "user": "testuser"}

        with patch('app.api.routes.service_connections.OAuth2ProviderFactory.get_supported_providers') as mock_get_providers:
            with patch('app.api.routes.service_connections.OAuth2ProviderFactory.create_provider') as mock_create_provider:
                with patch('app.core.encryption.decrypt_token') as mock_decrypt:
                    mock_get_providers.return_value = ["github"]

                    mock_provider = AsyncMock()
                    mock_provider.test_api_access.return_value = mock_test_result
                    mock_create_provider.return_value = mock_provider
                    mock_decrypt.return_value = "decrypted_token"

                    response = client.get(
                        f"/api/v1/service-connections/test/github/{connection.id}",
                        headers={"Authorization": f"Bearer {auth_token}"}
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["provider"] == "github"
                    assert data["test_result"] == mock_test_result

    def test_test_provider_api_access_unsupported_provider(self, client: SyncASGITestClient, auth_token: str, db_session: Session) -> None:
        """Test API access test with unsupported provider."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings
        import uuid

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create a connection for an unsupported provider
        connection = ServiceConnection(
            id=uuid.uuid4(),
            user_id=user_id,
            service_name="unsupported_provider",
            encrypted_access_token="encrypted_token",
        )
        db_session.add(connection)
        db_session.commit()

        with patch('app.api.routes.service_connections.OAuth2ProviderFactory.get_supported_providers') as mock_get_providers:
            mock_get_providers.return_value = []  # No supported providers

            response = client.get(
                f"/api/v1/service-connections/test/unsupported_provider/{connection.id}",
                headers={"Authorization": f"Bearer {auth_token}"}
            )

            assert response.status_code == 400
            assert "Unsupported provider" in response.json()["detail"]

    def test_test_provider_api_access_connection_not_found(self, client: SyncASGITestClient, auth_token: str) -> None:
        """Test API access test with nonexistent connection."""
        fake_id = uuid.uuid4()

        with patch('app.api.routes.service_connections.OAuth2ProviderFactory.get_supported_providers') as mock_get_providers:
            mock_get_providers.return_value = ["github"]

            response = client.get(
                f"/api/v1/service-connections/test/github/{fake_id}",
                headers={"Authorization": f"Bearer {auth_token}"}
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    def test_test_provider_api_access_unauthenticated(self, client: SyncASGITestClient) -> None:
        """Test API access test without authentication."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/service-connections/test/github/{fake_id}")
        assert response.status_code == 401

    def test_test_openai_api_key_connection_success(self, client: SyncASGITestClient, auth_token: str, db_session: Session) -> None:
        """Test successful OpenAI API key connection test."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings
        import uuid

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create a test API key connection
        connection = ServiceConnection(
            id=uuid.uuid4(),
            user_id=user_id,
            service_name="openai",
            encrypted_access_token="encrypted_api_key",
            oauth_metadata={"connection_type": "api_key"}  # Mark as API key connection
        )
        db_session.add(connection)
        db_session.commit()

        # Mock the httpx client and its get method
        with patch('app.api.routes.service_connections.httpx.AsyncClient') as mock_httpx_client_class:
            # Create a mock client instance
            mock_client_instance = AsyncMock()
            mock_httpx_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock the response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client_instance.get.return_value = mock_response

            # Mock the token decryption
            with patch('app.core.encryption.decrypt_token') as mock_decrypt:
                mock_decrypt.return_value = "sk-test-api-key"

                response = client.get(
                    f"/api/v1/service-connections/test/openai/{connection.id}",
                    headers={"Authorization": f"Bearer {auth_token}"}
                )

                # Verify that the API key was tested properly
                mock_client_instance.get.assert_called_once_with(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": "Bearer sk-test-api-key"},
                    timeout=10.0
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["provider"] == "openai"
                assert data["test_result"] == {"token_valid": True}

    def test_test_openai_api_key_connection_invalid_key(self, client: SyncASGITestClient, auth_token: str, db_session: Session) -> None:
        """Test OpenAI API key connection test with invalid key."""
        # Get user ID from token
        from jose import jwt
        from app.core.config import settings
        import uuid

        payload = jwt.decode(auth_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])

        # Create a test API key connection
        connection = ServiceConnection(
            id=uuid.uuid4(),
            user_id=user_id,
            service_name="openai",
            encrypted_access_token="encrypted_api_key",
            oauth_metadata={"connection_type": "api_key"}  # Mark as API key connection
        )
        db_session.add(connection)
        db_session.commit()

        # Mock the httpx client and its get method with 401 response
        with patch('app.api.routes.service_connections.httpx.AsyncClient') as mock_httpx_client_class:
            # Create a mock client instance
            mock_client_instance = AsyncMock()
            mock_httpx_client_class.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock the response with 401 error
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_client_instance.get.return_value = mock_response

            # Mock the token decryption
            with patch('app.core.encryption.decrypt_token') as mock_decrypt:
                mock_decrypt.return_value = "sk-invalid-api-key"

                response = client.get(
                    f"/api/v1/service-connections/test/openai/{connection.id}",
                    headers={"Authorization": f"Bearer {auth_token}"}
                )

                assert response.status_code == 400
                assert "Authentication failed" in response.json()["detail"]


class TestServiceConnectionsIntegration:
    """Integration tests for service connections."""

    def test_create_service_connection_with_metadata(self, db_session: Session) -> None:
        """Test creating service connection with OAuth metadata."""
        from app.services.service_connections import create_service_connection
        from app.schemas.service_connection import ServiceConnectionCreate

        user_id = uuid.uuid4()
        metadata = {
            "provider": "github",
            "user_info": {"id": 123, "login": "testuser"},
            "scopes": ["repo", "user:email"],
            "token_type": "Bearer"
        }

        connection_data = ServiceConnectionCreate(
            service_name="github",
            access_token="test_token",
            refresh_token="test_refresh"
        )

        connection = create_service_connection(db_session, connection_data, user_id, metadata)

        assert connection.oauth_metadata == metadata
        assert connection.service_name == "github"
        assert connection.user_id == user_id

    def test_service_connection_schema_excludes_tokens(self) -> None:
        """Test that ServiceConnectionRead schema excludes sensitive tokens."""
        from app.schemas.service_connection import ServiceConnectionRead

        # Check that sensitive fields are not in the schema
        schema_fields = ServiceConnectionRead.model_fields.keys()
        assert "encrypted_access_token" not in schema_fields
        assert "encrypted_refresh_token" not in schema_fields

        # Check that safe fields are included
        assert "id" in schema_fields
        assert "user_id" in schema_fields
        assert "service_name" in schema_fields
        assert "oauth_metadata" in schema_fields