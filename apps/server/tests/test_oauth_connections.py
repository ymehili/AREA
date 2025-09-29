"""Tests for OAuthConnectionService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock, patch
import pytest
from sqlalchemy.orm import Session

from app.services.oauth_connections import OAuthConnectionService
from app.services.service_connections import DuplicateServiceConnectionError
from app.integrations.oauth.exceptions import OAuth2Error
from app.models.service_connection import ServiceConnection


class TestOAuthConnectionService:
    """Test OAuthConnectionService functionality."""

    def test_generate_oauth_state(self) -> None:
        """Test OAuth state generation."""
        state1 = OAuthConnectionService.generate_oauth_state()
        state2 = OAuthConnectionService.generate_oauth_state()

        # States should be different and non-empty
        assert state1 != state2
        assert len(state1) > 10
        assert len(state2) > 10

    def test_get_authorization_url(self) -> None:
        """Test getting authorization URL."""
        with patch('app.services.oauth_connections.OAuth2ProviderFactory.create_provider') as mock_create:
            mock_provider = Mock()
            mock_provider.get_authorization_url.return_value = "https://github.com/login/oauth/authorize?state=test"
            mock_create.return_value = mock_provider

            url = OAuthConnectionService.get_authorization_url("github", "test_state")

            assert url == "https://github.com/login/oauth/authorize?state=test"
            mock_create.assert_called_once_with("github")
            mock_provider.get_authorization_url.assert_called_once_with("test_state")

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_success(self, db_session: Session) -> None:
        """Test successful OAuth callback handling."""
        user_id = str(uuid.uuid4())
        provider_name = "github"
        code = "test_code"

        # Mock the provider
        mock_token_set = Mock()
        mock_token_set.access_token = "access_token_123"
        mock_token_set.refresh_token = "refresh_token_123"
        mock_token_set.scope = "repo,user:email"
        mock_token_set.token_type = "Bearer"

        mock_user_info = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com"
        }

        mock_provider = AsyncMock()
        mock_provider.exchange_code_for_tokens.return_value = mock_token_set
        mock_provider.get_user_info.return_value = mock_user_info

        with patch('app.services.oauth_connections.OAuth2ProviderFactory.create_provider') as mock_create:
            with patch('app.services.oauth_connections.get_service_connection_by_user_and_service') as mock_get_existing:
                with patch('app.services.oauth_connections.create_service_connection') as mock_create_connection:
                    mock_create.return_value = mock_provider
                    mock_get_existing.return_value = None  # No existing connection

                    # Mock the created connection
                    mock_connection = Mock()
                    mock_connection.id = uuid.uuid4()
                    mock_create_connection.return_value = mock_connection

                    # Test the callback
                    result = await OAuthConnectionService.handle_oauth_callback(
                        provider_name, code, user_id, db_session
                    )

                    # Verify the result
                    assert result == mock_connection

                    # Verify the OAuth metadata was created correctly
                    expected_metadata = {
                        "provider": provider_name,
                        "user_info": {
                            "id": 12345,
                            "login": "testuser",
                            "name": "Test User",
                            "email": "test@example.com",
                        },
                        "scopes": ["repo", "user:email"],
                        "token_type": "Bearer",
                    }

                    # Verify create_service_connection was called with metadata
                    mock_create_connection.assert_called_once()
                    call_args = mock_create_connection.call_args
                    # Check the positional arguments and keyword arguments
                    assert len(call_args[0]) >= 3  # db, connection_data, user_id
                    if len(call_args) > 1 and 'oauth_metadata' in call_args[1]:
                        assert call_args[1]['oauth_metadata'] == expected_metadata
                    elif len(call_args[0]) > 3:  # oauth_metadata as positional argument
                        assert call_args[0][3] == expected_metadata

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_duplicate_connection(self, db_session: Session) -> None:
        """Test OAuth callback with existing connection raises error."""
        user_id = str(uuid.uuid4())
        provider_name = "github"
        code = "test_code"

        # Mock existing connection
        existing_connection = Mock()
        existing_connection.id = uuid.uuid4()

        with patch('app.services.oauth_connections.get_service_connection_by_user_and_service') as mock_get_existing:
            mock_get_existing.return_value = existing_connection

            with pytest.raises(DuplicateServiceConnectionError):
                await OAuthConnectionService.handle_oauth_callback(
                    provider_name, code, user_id, db_session
                )

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_provider_error(self, db_session: Session) -> None:
        """Test OAuth callback with provider error."""
        user_id = str(uuid.uuid4())
        provider_name = "github"
        code = "test_code"

        mock_provider = AsyncMock()
        mock_provider.exchange_code_for_tokens.side_effect = Exception("Provider error")

        with patch('app.services.oauth_connections.OAuth2ProviderFactory.create_provider') as mock_create:
            with patch('app.services.oauth_connections.get_service_connection_by_user_and_service') as mock_get_existing:
                mock_create.return_value = mock_provider
                mock_get_existing.return_value = None

                with pytest.raises(OAuth2Error):
                    await OAuthConnectionService.handle_oauth_callback(
                        provider_name, code, user_id, db_session
                    )

    @pytest.mark.asyncio
    async def test_validate_connection_success(self) -> None:
        """Test successful connection validation."""
        # Create a mock connection with metadata
        connection = Mock(spec=ServiceConnection)
        connection.oauth_metadata = {
            "provider": "github",
            "user_info": {"id": 123},
            "scopes": ["repo"],
            "token_type": "Bearer"
        }
        connection.encrypted_access_token = "encrypted_token"

        mock_provider = AsyncMock()
        mock_provider.validate_token.return_value = True

        with patch('app.services.oauth_connections.OAuth2ProviderFactory.create_provider') as mock_create:
            with patch('app.core.encryption.decrypt_token') as mock_decrypt:
                mock_create.return_value = mock_provider
                mock_decrypt.return_value = "decrypted_token"

                result = await OAuthConnectionService.validate_connection(connection)

                assert result is True
                mock_provider.validate_token.assert_called_once_with("decrypted_token")

    @pytest.mark.asyncio
    async def test_validate_connection_no_metadata(self) -> None:
        """Test connection validation with no metadata."""
        connection = Mock(spec=ServiceConnection)
        connection.oauth_metadata = None

        result = await OAuthConnectionService.validate_connection(connection)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_connection_no_provider(self) -> None:
        """Test connection validation with missing provider in metadata."""
        connection = Mock(spec=ServiceConnection)
        connection.oauth_metadata = {"user_info": {"id": 123}}

        result = await OAuthConnectionService.validate_connection(connection)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_connection_exception(self) -> None:
        """Test connection validation with exception."""
        connection = Mock(spec=ServiceConnection)
        connection.oauth_metadata = {"provider": "github"}
        connection.encrypted_access_token = "encrypted_token"

        mock_provider = AsyncMock()
        mock_provider.validate_token.side_effect = Exception("Validation error")

        with patch('app.services.oauth_connections.OAuth2ProviderFactory.create_provider') as mock_create:
            with patch('app.core.encryption.decrypt_token') as mock_decrypt:
                mock_create.return_value = mock_provider
                mock_decrypt.return_value = "decrypted_token"

                result = await OAuthConnectionService.validate_connection(connection)
                assert result is False

    @pytest.mark.asyncio
    async def test_get_connection_user_info_success(self) -> None:
        """Test successful user info retrieval."""
        connection = Mock(spec=ServiceConnection)
        connection.oauth_metadata = {
            "provider": "github",
            "user_info": {"id": 123}
        }
        connection.encrypted_access_token = "encrypted_token"

        mock_user_info = {"id": 123, "login": "testuser", "name": "Test User"}
        mock_provider = AsyncMock()
        mock_provider.get_user_info.return_value = mock_user_info

        with patch('app.services.oauth_connections.OAuth2ProviderFactory.create_provider') as mock_create:
            with patch('app.core.encryption.decrypt_token') as mock_decrypt:
                mock_create.return_value = mock_provider
                mock_decrypt.return_value = "decrypted_token"

                result = await OAuthConnectionService.get_connection_user_info(connection)

                assert result == mock_user_info
                mock_provider.get_user_info.assert_called_once_with("decrypted_token")

    @pytest.mark.asyncio
    async def test_get_connection_user_info_no_metadata(self) -> None:
        """Test user info retrieval with no metadata."""
        connection = Mock(spec=ServiceConnection)
        connection.oauth_metadata = None

        result = await OAuthConnectionService.get_connection_user_info(connection)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_connection_user_info_exception(self) -> None:
        """Test user info retrieval with exception."""
        connection = Mock(spec=ServiceConnection)
        connection.oauth_metadata = {"provider": "github"}
        connection.encrypted_access_token = "encrypted_token"

        mock_provider = AsyncMock()
        mock_provider.get_user_info.side_effect = Exception("API error")

        with patch('app.services.oauth_connections.OAuth2ProviderFactory.create_provider') as mock_create:
            with patch('app.core.encryption.decrypt_token') as mock_decrypt:
                mock_create.return_value = mock_provider
                mock_decrypt.return_value = "decrypted_token"

                result = await OAuthConnectionService.get_connection_user_info(connection)
                assert result is None