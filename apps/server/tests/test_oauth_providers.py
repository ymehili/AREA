"""Tests for OAuth providers."""

from __future__ import annotations

from unittest.mock import Mock, patch, AsyncMock
import pytest
import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

from app.integrations.oauth.base import OAuth2Config
from app.integrations.oauth.exceptions import (
    OAuth2RefreshError,
    OAuth2TokenExchangeError,
    OAuth2ValidationError,
)
from app.integrations.oauth.providers.github import GitHubOAuth2Provider
from app.integrations.oauth.providers.gmail import GmailOAuth2Provider
from app.integrations.oauth.providers.outlook import OutlookOAuth2Provider


class TestGitHubOAuth2Provider:
    """Test GitHub OAuth2 provider functionality."""

    def test_get_authorization_url(self):
        """Test GitHub authorization URL generation."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=["repo", "user:email"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GitHubOAuth2Provider(config)

        url = provider.get_authorization_url("test_state")

        assert "https://github.com/login/oauth/authorize" in url
        assert "client_id=test_client_id" in url
        assert "state=test_state" in url

    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self):
        """Test GitHub code exchange for token."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=["repo", "user:email"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GitHubOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.github.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "test_token",
                "token_type": "bearer",
                "scope": "repo,user:email"
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await provider.exchange_code_for_tokens("test_code")

            assert result.access_token == "test_token"
            assert result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token(self):
        """Test GitHub token refresh raises error (GitHub doesn't support refresh)."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=["repo", "user:email"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GitHubOAuth2Provider(config)

        # GitHub doesn't support token refresh, so this should raise an error
        with pytest.raises(OAuth2RefreshError):
            await provider.refresh_tokens("refresh_token")

    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test GitHub user info retrieval."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=["repo", "user:email"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GitHubOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.github.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": 12345,
                "login": "testuser",
                "email": "test@example.com",
                "name": "Test User"
            }
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.get_user_info("test_token")

            assert result["id"] == 12345
            assert result["login"] == "testuser"
            assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_error(self):
        """Test GitHub code exchange with error response."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=["repo", "user:email"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GitHubOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.github.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("Bad Request")
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception):
                await provider.exchange_code_for_tokens("invalid_code")

    @pytest.mark.asyncio
    async def test_get_user_info_error(self):
        """Test GitHub user info retrieval with error."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=["repo", "user:email"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GitHubOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.github.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("Unauthorized")
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception):
                await provider.get_user_info("invalid_token")


class TestGmailOAuth2Provider:
    """Test Gmail OAuth2 provider functionality."""

    def test_get_authorization_url(self):
        """Test Gmail authorization URL generation."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GmailOAuth2Provider(config)

        url = provider.get_authorization_url("test_state")

        assert "https://accounts.google.com/o/oauth2/v2/auth" in url
        assert "client_id=test_client_id" in url
        assert "state=test_state" in url

    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self):
        """Test Gmail code exchange for token."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "test_token",
                "refresh_token": "refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/gmail.modify"
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await provider.exchange_code_for_tokens("test_code")

            assert result.access_token == "test_token"
            assert result.refresh_token == "refresh_token"
            assert result.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_refresh_token(self):
        """Test Gmail token refresh."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "new_token",
                "token_type": "Bearer",
                "expires_in": 3600
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await provider.refresh_tokens("refresh_token")

            assert result.access_token == "new_token"
            assert result.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test Gmail user info retrieval."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "email": "test@example.com",
                "name": "Test User",
                "sub": "123456"
            }
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.get_user_info("test_token")

            assert result["email"] == "test@example.com"
            assert result["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_error(self):
        """Test Gmail code exchange with error response."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("Bad Request")
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception):
                await provider.exchange_code_for_tokens("invalid_code")

    @pytest.mark.asyncio
    async def test_get_user_info_error(self):
        """Test Gmail user info retrieval with error."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("Unauthorized")
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception):
                await provider.get_user_info("invalid_token")

    @pytest.mark.asyncio
    async def test_refresh_token_error(self):
        """Test Gmail token refresh with error."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Bad Request", request=Mock(), response=Mock())
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(OAuth2RefreshError):
                await provider.refresh_tokens("invalid_refresh_token")

    @pytest.mark.asyncio
    async def test_github_provider_name(self):
        """Test GitHub provider name property."""
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GitHubOAuth2Provider(config)
        assert provider.provider_name == "github"

    @pytest.mark.asyncio
    async def test_gmail_provider_name(self):
        """Test Gmail provider name property."""
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GmailOAuth2Provider(config)
        assert provider.provider_name == "gmail"

    @pytest.mark.asyncio
    async def test_github_exchange_with_error_in_response(self):
        """Test GitHub token exchange with error in JSON response."""
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GitHubOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.github.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"error": "invalid_grant"}
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(OAuth2TokenExchangeError):
                await provider.exchange_code_for_tokens("bad_code")

    @pytest.mark.asyncio
    async def test_gmail_exchange_with_error_in_response(self):
        """Test Gmail token exchange with error in JSON response."""
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"error": "invalid_grant"}
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(OAuth2TokenExchangeError):
                await provider.exchange_code_for_tokens("bad_code")

    @pytest.mark.asyncio
    async def test_gmail_refresh_with_error_in_response(self):
        """Test Gmail token refresh with error in JSON response."""
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"error": "invalid_grant"}
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(OAuth2RefreshError):
                await provider.refresh_tokens("bad_refresh_token")

    @pytest.mark.asyncio
    async def test_github_validate_token_success(self):
        """Test GitHub token validation success."""
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GitHubOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.github.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"login": "testuser"}
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.validate_token("valid_token")
            assert result is True

    @pytest.mark.asyncio
    async def test_github_validate_token_failure(self):
        """Test GitHub token validation failure."""
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GitHubOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.github.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Unauthorized", request=Mock(), response=Mock())
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.validate_token("invalid_token")
            assert result is False
            assert result is False

    @pytest.mark.asyncio
    async def test_gmail_validate_token_success(self):
        """Test Gmail token validation success."""
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"email": "test@example.com"}
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.validate_token("valid_token")
            assert result is True

    @pytest.mark.asyncio
    async def test_gmail_validate_token_failure(self):
        """Test Gmail token validation failure."""
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Unauthorized", request=Mock(), response=Mock())
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.validate_token("invalid_token")
            assert result is False
            assert result is False

    @pytest.mark.asyncio
    async def test_github_http_error_handling(self):
        """Test GitHub HTTP error handling."""
        import httpx
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GitHubOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.github.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Network error")
            )

            with pytest.raises(OAuth2TokenExchangeError):
                await provider.exchange_code_for_tokens("code")

    @pytest.mark.asyncio
    async def test_gmail_http_error_handling(self):
        """Test Gmail HTTP error handling."""
        import httpx
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Network error")
            )

            with pytest.raises(OAuth2TokenExchangeError):
                await provider.exchange_code_for_tokens("code")

    @pytest.mark.asyncio
    async def test_gmail_user_info_http_error(self):
        """Test Gmail user info HTTP error handling."""
        import httpx
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GmailOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.gmail.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Network error")
            )

            with pytest.raises(OAuth2ValidationError):
                await provider.get_user_info("token")

    @pytest.mark.asyncio
    async def test_github_user_info_http_error(self):
        """Test GitHub user info HTTP error handling."""
        import httpx
        config = OAuth2Config(
            client_id="test", client_secret="test",
            authorization_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes=[], redirect_uri="http://test"
        )
        provider = GitHubOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.github.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Network error")
            )

            with pytest.raises(OAuth2ValidationError):
                await provider.get_user_info("token")

            with pytest.raises(Exception):
                await provider.refresh_tokens("invalid_refresh_token")


class TestOutlookOAuth2Provider:
    """Test Outlook OAuth2 provider functionality."""

    def test_get_authorization_url(self):
        """Test Outlook authorization URL generation."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        url = provider.get_authorization_url("test_state")

        assert "https://login.microsoftonline.com/common/oauth2/v2.0/authorize" in url
        assert "client_id=test_client_id" in url
        assert "state=test_state" in url
        assert "response_type=code" in url

    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self):
        """Test Outlook code exchange for token."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.outlook.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "test_token",
                "refresh_token": "refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "User.Read Mail.ReadWrite Mail.Send"
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await provider.exchange_code_for_tokens("test_code")

            assert result.access_token == "test_token"
            assert result.refresh_token == "refresh_token"
            assert result.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_refresh_token(self):
        """Test Outlook token refresh."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.outlook.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "access_token": "new_token",
                "refresh_token": "new_refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await provider.refresh_tokens("refresh_token")

            assert result.access_token == "new_token"
            assert result.refresh_token == "new_refresh_token"
            assert result.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test Outlook user info retrieval."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.outlook.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "12345",
                "userPrincipalName": "test@example.com",
                "displayName": "Test User",
                "mail": "test@example.com"
            }
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.get_user_info("test_token")

            assert result["id"] == "12345"
            assert result["userPrincipalName"] == "test@example.com"
            assert result["displayName"] == "Test User"

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_error(self):
        """Test Outlook code exchange with error response."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.outlook.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("Bad Request")
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception):
                await provider.exchange_code_for_tokens("invalid_code")

    @pytest.mark.asyncio
    async def test_get_user_info_error(self):
        """Test Outlook user info retrieval with error."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.outlook.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("Unauthorized")
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception):
                await provider.get_user_info("invalid_token")

    @pytest.mark.asyncio
    async def test_refresh_token_error(self):
        """Test Outlook token refresh with error."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.outlook.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = Exception("Bad Request")
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(Exception):
                await provider.refresh_tokens("invalid_refresh_token")

    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        """Test Outlook token validation success."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.outlook.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "12345"}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.validate_token("valid_token")

            assert result is True

    @pytest.mark.asyncio
    async def test_validate_token_expired(self):
        """Test Outlook token validation with expired token."""
        from app.integrations.oauth.exceptions import OAuth2ValidationError
        
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.outlook.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=Mock(),
                response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await provider.validate_token("expired_token")

            assert result is False

    @pytest.mark.asyncio
    async def test_test_api_access_success(self):
        """Test Outlook API access test success."""
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.outlook.httpx.AsyncClient") as mock_client:
            # Mock user profile response
            mock_user_response = Mock()
            mock_user_response.status_code = 200
            mock_user_response.raise_for_status = Mock()
            mock_user_response.json.return_value = {
                "id": "12345",
                "userPrincipalName": "test@example.com",
                "displayName": "Test User"
            }
            
            # Mock folders response
            mock_folders_response = Mock()
            mock_folders_response.status_code = 200
            mock_folders_response.raise_for_status = Mock()
            mock_folders_response.json.return_value = {
                "value": [
                    {"id": "folder1", "displayName": "Inbox", "totalItemCount": 10, "unreadItemCount": 2}
                ]
            }
            
            # Mock inbox response
            mock_inbox_response = Mock()
            mock_inbox_response.status_code = 200
            mock_inbox_response.raise_for_status = Mock()
            mock_inbox_response.json.return_value = {
                "totalItemCount": 100,
                "unreadItemCount": 5
            }

            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = [
                mock_user_response,
                mock_folders_response,
                mock_inbox_response
            ]
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await provider.test_api_access("valid_token")

            assert "profile" in result
            assert "mailbox" in result
            assert "folders" in result
            assert result["profile"]["id"] == "12345"

    @pytest.mark.asyncio
    async def test_test_api_access_failure(self):
        """Test Outlook API access test failure."""
        from app.integrations.oauth.exceptions import OAuth2ValidationError
        
        config = OAuth2Config(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            scopes=["User.Read", "Mail.ReadWrite", "Mail.Send"],
            redirect_uri="http://localhost:8080/callback"
        )
        provider = OutlookOAuth2Provider(config)

        with patch("app.integrations.oauth.providers.outlook.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "403 Forbidden",
                request=Mock(),
                response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(OAuth2ValidationError):
                await provider.test_api_access("invalid_token")
