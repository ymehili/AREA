"""Tests for Google Calendar OAuth provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import HTTPStatusError, RequestError
import httpx

from app.integrations.oauth.providers.google_calendar import GoogleCalendarOAuth2Provider
from app.integrations.oauth.exceptions import (
    OAuth2RefreshError,
    OAuth2TokenExchangeError,
    OAuth2ValidationError,
)


class TestGoogleCalendarOAuth2Provider:
    """Test Google Calendar OAuth provider implementation."""

    @pytest.fixture
    def provider(self):
        """Create a mock GoogleCalendarOAuth2Provider instance."""
        mock_config = MagicMock()
        mock_config.client_id = "test_client_id"
        mock_config.client_secret = "test_client_secret"
        mock_config.redirect_uri = "http://localhost/callback"
        mock_config.authorization_url = "https://accounts.google.com/oauth"
        mock_config.token_url = "https://oauth2.googleapis.com/token"
        mock_config.scopes = ["https://www.googleapis.com/auth/calendar"]

        provider = GoogleCalendarOAuth2Provider(config=mock_config)
        return provider

    def test_provider_name(self, provider):
        """Test provider name property."""
        assert provider.provider_name == "google_calendar"

    def test_get_authorization_url(self, provider):
        """Test generating authorization URL."""
        state = "test_state"
        url = provider.get_authorization_url(state)

        # Check that the URL contains required parameters
        assert "client_id=test_client_id" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
        assert "scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar" in url
        assert "state=test_state" in url
        assert "response_type=code" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self, provider):
        """Test exchanging authorization code for tokens."""
        mock_response_data = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a mock response that behaves like a real httpx response
            # where json() is a synchronous method
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_response.content = b"{}"

            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await provider.exchange_code_for_tokens("test_code")
            # Verify the result
            assert result.access_token == "test_access_token"
            assert result.refresh_token == "test_refresh_token"
            assert result.expires_in == 3600
            assert result.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_with_error_in_response(self, provider):
        """Test handling OAuth error in token response."""
        mock_response_data = {"error": "invalid_grant"}

        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a mock response that behaves like a real httpx response
            # where json() is a synchronous method
            mock_response = MagicMock()
            # Properly mock the response methods
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_response.content = b"{}"
            
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            with pytest.raises(OAuth2TokenExchangeError):
                await provider.exchange_code_for_tokens("test_code")

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_http_error(self, provider):
        """Test handling HTTP errors during token exchange."""
        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a mock response that behaves like a real httpx response
            # where json() is a synchronous method
            mock_response = MagicMock()
            # Use AsyncMock for the raise_for_status method to handle the error properly
            mock_response.raise_for_status.side_effect = HTTPStatusError(
                "Request failed", request=MagicMock(), response=MagicMock()
            )
            mock_response.json.return_value = {"error": "request_failed"}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            with pytest.raises(OAuth2TokenExchangeError):
                await provider.exchange_code_for_tokens("test_code")

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self, provider):
        """Test refreshing tokens."""
        mock_response_data = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a mock response that behaves like a real httpx response
            # where json() is a synchronous method
            mock_response = MagicMock()
            # Properly mock the response methods
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_response.content = b"{}"
            
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            result = await provider.refresh_tokens("test_refresh_token")
            if hasattr(result, '__await__'):
                result = await result
            # Verify the result
            assert result.access_token == "new_access_token"
            assert result.refresh_token == "test_refresh_token"  # Refresh token stays the same
            assert result.expires_in == 3600
            assert result.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_refresh_tokens_with_error_in_response(self, provider):
        """Test handling OAuth error in refresh token response."""
        mock_response_data = {"error": "invalid_grant"}

        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a mock response that behaves like a real httpx response
            # where json() is a synchronous method
            mock_response = MagicMock()
            # Properly mock the response methods
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_response_data
            mock_response.content = b"{}"
            
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            with pytest.raises(OAuth2RefreshError):
                await provider.refresh_tokens("test_refresh_token")

    @pytest.mark.asyncio
    async def test_refresh_tokens_http_error(self, provider):
        """Test handling HTTP errors during token refresh."""
        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a mock response that behaves like a real httpx response
            # where json() is a synchronous method
            mock_response = MagicMock()
            # Use AsyncMock for the raise_for_status method to handle the error properly
            mock_response.raise_for_status.side_effect = HTTPStatusError(
                "Request failed", request=MagicMock(), response=MagicMock()
            )
            mock_response.json.return_value = {"error": "request_failed"}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            with pytest.raises(OAuth2RefreshError):
                await provider.refresh_tokens("test_refresh_token")

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, provider):
        """Test getting user information."""
        mock_user_data = {
            "id": "123456789",
            "email": "test @example.com",
            "name": "Test User",
            "verified_email": True,
        }

        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a mock response that behaves like a real httpx response
            # where json() is a synchronous method
            mock_response = MagicMock()
            # Properly mock the response methods
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_user_data
            mock_response.content = b"{}"
            
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            result = await provider.get_user_info("test_access_token")
            if hasattr(result, '__await__'):
                result = await result
            # Verify the result
            assert result == mock_user_data

    @pytest.mark.asyncio
    async def test_get_user_info_http_error(self, provider):
        """Test handling HTTP errors when getting user info."""
        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a mock response that behaves like a real httpx response
            # where json() is a synchronous method
            mock_response = MagicMock()
            # Use AsyncMock for the raise_for_status method to handle the error properly
            mock_response.raise_for_status.side_effect = HTTPStatusError(
                "Request failed", request=MagicMock(), response=MagicMock()
            )
            mock_response.json.return_value = {"error": "request_failed"}
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            with pytest.raises(OAuth2ValidationError):
                await provider.get_user_info("test_access_token")

    @pytest.mark.asyncio
    async def test_validate_token_success(self, provider):
        """Test validating an access token."""
        mock_user_data = {
            "id": "123456789",
            "email": "test @example.com",
            "name": "Test User",
            "verified_email": True,
        }

        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a mock response that behaves like a real httpx response
            # where json() is a synchronous method
            mock_response = MagicMock()
            # Properly mock the response methods
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = mock_user_data
            mock_response.content = b"{}"
            
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            result = await provider.validate_token("test_access_token")

            # Verify the result
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_token_failure(self, provider):
        """Test validating an invalid access token."""
        with patch.object(provider, 'get_user_info') as mock_get_user_info:
            mock_get_user_info.side_effect = OAuth2ValidationError("Token invalid")

            result = await provider.validate_token("invalid_token")

            # Verify the result
            assert result is False

    @pytest.mark.asyncio
    async def test_test_api_access_success(self, provider):
        """Test testing API access."""
        mock_calendar_data = {
            "items": [
                {
                    "id": "primary",
                    "summary": "Primary Calendar",
                    "primary": True,
                }
            ]
        }
        mock_primary_data = {
            "id": "primary",
            "summary": "Primary Calendar",
            "timeZone": "UTC"
        }

        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            
            # Create different responses for different requests
            async def get_side_effect(*args, **kwargs):
                if "calendarList" in str(args[0]) if args else False:
                    # Create a mock response that behaves like a real httpx response
                    # where json() is a synchronous method
                    mock_response = MagicMock()
                    # Properly mock the response methods
                    mock_response.raise_for_status.return_value = None
                    mock_response.json.return_value = mock_calendar_data
                    mock_response.content = b"{}"
                    return mock_response
                elif "calendars/primary" in str(args[0]) if args else False:
                    # Create a mock response that behaves like a real httpx response
                    # where json() is a synchronous method
                    mock_response = MagicMock()
                    # Properly mock the response methods
                    mock_response.raise_for_status.return_value = None
                    mock_response.json.return_value = mock_primary_data
                    mock_response.content = b"{}"
                    return mock_response
                else:
                    # Create a mock response that behaves like a real httpx response
                    # where json() is a synchronous method
                    mock_response = MagicMock()
                    # Properly mock the response methods
                    mock_response.raise_for_status.return_value = None
                    mock_response.json.return_value = {}
                    mock_response.content = b"{}"
                    return mock_response
            
            mock_client.get = AsyncMock(side_effect=get_side_effect)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            result = await provider.test_api_access("test_access_token")

            # Verify the result
            assert result["primary_calendar"]["id"] == "primary"
            assert result["primary_calendar"]["summary"] == "Primary Calendar"
            assert result["primary_calendar"]["timezone"] == "UTC"
            assert len(result["calendars"]) == 1

    @pytest.mark.asyncio
    async def test_test_api_access_http_error(self, provider):
        """Test handling HTTP errors during API access test."""
        with patch("app.integrations.oauth.providers.google_calendar.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create a mock response that behaves like a real httpx response
            # where json() is a synchronous method
            mock_response = MagicMock()
            # Use AsyncMock for the raise_for_status method to handle the error properly
            mock_response.raise_for_status.side_effect = HTTPStatusError(
                "Request failed", request=MagicMock(), response=MagicMock()
            )
            mock_response.json.return_value = {"error": "request_failed"}
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)

            with pytest.raises(OAuth2ValidationError):
                await provider.test_api_access("test_access_token")