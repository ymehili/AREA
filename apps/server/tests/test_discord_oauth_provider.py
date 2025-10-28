"""Tests for Discord OAuth2 provider."""

from __future__ import annotations

from unittest.mock import Mock, AsyncMock, patch
import pytest
import httpx

from app.integrations.oauth.base import OAuth2Config
from app.integrations.oauth.exceptions import (
    OAuth2RefreshError,
    OAuth2TokenExchangeError,
    OAuth2ValidationError,
)
from app.integrations.oauth.providers.discord import DiscordOAuth2Provider


class TestDiscordOAuth2Provider:
    """Test Discord OAuth2 provider functionality."""

    @pytest.fixture
    def config(self):
        """Create test OAuth2 config for Discord."""
        return OAuth2Config(
            client_id="test_discord_client_id",
            client_secret="test_discord_client_secret",
            authorization_url="https://discord.com/api/oauth2/authorize",
            token_url="https://discord.com/api/oauth2/token",
            scopes=["bot", "identify"],
            redirect_uri="http://localhost:8080/api/v1/service-connections/callback/discord"
        )

    @pytest.fixture
    def provider(self, config):
        """Create Discord OAuth2 provider instance."""
        return DiscordOAuth2Provider(config)

    def test_provider_name(self, provider):
        """Test Discord provider name."""
        assert provider.provider_name == "discord"

    def test_get_authorization_url(self, provider):
        """Test Discord authorization URL generation."""
        url = provider.get_authorization_url("test_state")

        assert "https://discord.com/api/oauth2/authorize" in url
        assert "client_id=test_discord_client_id" in url
        assert "state=test_state" in url
        assert "scope=bot+identify" in url or "scope=bot%20identify" in url
        assert "response_type=code" in url
        assert "permissions=68624" in url  # Bot permissions

    def test_get_authorization_url_with_custom_permissions(self, provider):
        """Test Discord authorization URL with custom bot permissions."""
        url = provider.get_authorization_url("test_state", permissions=8)

        # Should still use default permissions from the method
        assert "permissions=68624" in url

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self, provider):
        """Test successful Discord code exchange for tokens."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "test_discord_token",
                "refresh_token": "test_refresh_token",
                "token_type": "Bearer",
                "expires_in": 604800,
                "scope": "bot identify"
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await provider.exchange_code_for_tokens("test_code")

            assert result.access_token == "test_discord_token"
            assert result.refresh_token == "test_refresh_token"
            assert result.token_type == "Bearer"
            assert result.expires_in == 604800
            assert result.scope == "bot identify"

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_with_error_in_response(self, provider):
        """Test Discord code exchange when response contains error."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "error": "invalid_grant",
                "error_description": "Invalid authorization code"
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(OAuth2TokenExchangeError) as exc_info:
                await provider.exchange_code_for_tokens("invalid_code")

            assert "Discord OAuth error" in str(exc_info.value)
            assert "invalid_grant" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_http_error(self, provider):
        """Test Discord code exchange with HTTP error."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Connection failed")
            )

            with pytest.raises(OAuth2TokenExchangeError) as exc_info:
                await provider.exchange_code_for_tokens("test_code")

            assert "Failed to exchange code" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self, provider):
        """Test successful Discord token refresh."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "new_discord_token",
                "refresh_token": "new_refresh_token",
                "token_type": "Bearer",
                "expires_in": 604800,
                "scope": "bot identify"
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await provider.refresh_tokens("old_refresh_token")

            assert result.access_token == "new_discord_token"
            assert result.refresh_token == "new_refresh_token"
            assert result.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_refresh_tokens_keeps_old_refresh_token(self, provider):
        """Test Discord token refresh keeps old refresh token if new one not provided."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "new_discord_token",
                "token_type": "Bearer",
                "expires_in": 604800
                # No refresh_token in response
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await provider.refresh_tokens("old_refresh_token")

            assert result.access_token == "new_discord_token"
            assert result.refresh_token == "old_refresh_token"  # Kept old one

    @pytest.mark.asyncio
    async def test_refresh_tokens_with_error_in_response(self, provider):
        """Test Discord token refresh when response contains error."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "error": "invalid_grant",
                "error_description": "Invalid refresh token"
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(OAuth2RefreshError) as exc_info:
                await provider.refresh_tokens("invalid_refresh_token")

            assert "Discord token refresh error" in str(exc_info.value)
            assert "invalid_grant" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_tokens_http_error(self, provider):
        """Test Discord token refresh with HTTP error."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Connection failed")
            )

            with pytest.raises(OAuth2RefreshError) as exc_info:
                await provider.refresh_tokens("test_refresh_token")

            assert "Failed to refresh token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, provider):
        """Test successful Discord user info retrieval."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "123456789",
                "username": "testuser",
                "discriminator": "1234",
                "global_name": "Test User",
                "email": "test@example.com",
                "verified": True,
                "avatar": "a_1234567890abcdef"
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.get_user_info("test_token")

            assert result["id"] == "123456789"
            assert result["username"] == "testuser"
            assert result["email"] == "test@example.com"
            assert result["verified"] is True

    @pytest.mark.asyncio
    async def test_get_user_info_http_error(self, provider):
        """Test Discord user info retrieval with HTTP error."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Unauthorized")
            )

            with pytest.raises(OAuth2ValidationError) as exc_info:
                await provider.get_user_info("invalid_token")

            assert "Failed to get user info" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_token_success(self, provider):
        """Test Discord token validation with valid token."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "123456789",
                "username": "testuser"
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.validate_token("valid_token")

            assert result is True

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, provider):
        """Test Discord token validation with invalid token."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Unauthorized")
            )

            result = await provider.validate_token("invalid_token")

            assert result is False

    @pytest.mark.asyncio
    async def test_test_api_access_success(self, provider):
        """Test Discord API access test with successful response."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_user_response = Mock()
            mock_user_response.json.return_value = {
                "id": "123456789",
                "username": "testuser",
                "discriminator": "1234",
                "global_name": "Test User",
                "email": "test@example.com",
                "verified": True,
                "avatar": "a_1234567890abcdef"
            }
            mock_user_response.raise_for_status = Mock()

            mock_guilds_response = Mock()
            mock_guilds_response.json.return_value = [
                {
                    "id": "guild1",
                    "name": "Test Server 1",
                    "icon": "icon1",
                    "owner": True,
                    "permissions": "8"
                },
                {
                    "id": "guild2",
                    "name": "Test Server 2",
                    "icon": "icon2",
                    "owner": False,
                    "permissions": "0"
                }
            ]
            mock_guilds_response.raise_for_status = Mock()

            mock_client_instance = mock_client.return_value.__aenter__.return_value
            mock_client_instance.get = AsyncMock(side_effect=[mock_user_response, mock_guilds_response])

            result = await provider.test_api_access("test_token")

            assert result["user"]["id"] == "123456789"
            assert result["user"]["username"] == "testuser"
            assert result["user"]["email"] == "test@example.com"
            assert result["guild_count"] == 2
            assert len(result["guilds"]) == 2
            assert result["guilds"][0]["name"] == "Test Server 1"

    @pytest.mark.asyncio
    async def test_test_api_access_with_many_guilds(self, provider):
        """Test Discord API access test returns max 10 guilds."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_user_response = Mock()
            mock_user_response.json.return_value = {
                "id": "123456789",
                "username": "testuser",
                "discriminator": "1234"
            }
            mock_user_response.raise_for_status = Mock()

            # Create 15 guilds
            guilds_data = [
                {"id": f"guild{i}", "name": f"Server {i}", "icon": None, "owner": False, "permissions": "0"}
                for i in range(15)
            ]
            mock_guilds_response = Mock()
            mock_guilds_response.json.return_value = guilds_data
            mock_guilds_response.raise_for_status = Mock()

            mock_client_instance = mock_client.return_value.__aenter__.return_value
            mock_client_instance.get = AsyncMock(side_effect=[mock_user_response, mock_guilds_response])

            result = await provider.test_api_access("test_token")

            assert result["guild_count"] == 15
            assert len(result["guilds"]) == 10  # Only first 10 returned

    @pytest.mark.asyncio
    async def test_test_api_access_http_error(self, provider):
        """Test Discord API access test with HTTP error."""
        with patch("app.integrations.oauth.providers.discord.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Unauthorized")
            )

            with pytest.raises(OAuth2ValidationError) as exc_info:
                await provider.test_api_access("invalid_token")

            assert "Failed to test API access" in str(exc_info.value)
