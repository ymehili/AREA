"""Tests for OAuth2ProviderFactory."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from app.integrations.oauth.factory import OAuth2ProviderFactory
from app.integrations.oauth.exceptions import UnsupportedProviderError
from app.integrations.oauth.providers.github import GitHubOAuth2Provider


class TestOAuth2ProviderFactory:
    """Test OAuth2ProviderFactory functionality."""

    def test_get_supported_providers_empty_when_no_config(self) -> None:
        """Test that no providers are returned when credentials are not configured."""
        with patch('app.integrations.oauth.factory.settings') as mock_settings:
            mock_settings.github_client_id = ""
            mock_settings.github_client_secret = ""

            providers = OAuth2ProviderFactory.get_supported_providers()
            assert providers == []

    def test_get_supported_providers_with_github_config(self) -> None:
        """Test that GitHub is returned when properly configured."""
        with patch('app.integrations.oauth.factory.settings') as mock_settings:
            mock_settings.github_client_id = "test_client_id"
            mock_settings.github_client_secret = "test_client_secret"

            providers = OAuth2ProviderFactory.get_supported_providers()
            assert "github" in providers

    def test_is_provider_configured_github_with_credentials(self) -> None:
        """Test provider configuration check with GitHub credentials."""
        with patch('app.integrations.oauth.factory.settings') as mock_settings:
            mock_settings.github_client_id = "test_client_id"
            mock_settings.github_client_secret = "test_client_secret"

            assert OAuth2ProviderFactory._is_provider_configured("github") is True

    def test_is_provider_configured_github_without_credentials(self) -> None:
        """Test provider configuration check without GitHub credentials."""
        with patch('app.integrations.oauth.factory.settings') as mock_settings:
            mock_settings.github_client_id = ""
            mock_settings.github_client_secret = ""

            assert OAuth2ProviderFactory._is_provider_configured("github") is False

    def test_is_provider_configured_github_partial_credentials(self) -> None:
        """Test provider configuration check with partial GitHub credentials."""
        with patch('app.integrations.oauth.factory.settings') as mock_settings:
            mock_settings.github_client_id = "test_client_id"
            mock_settings.github_client_secret = ""

            assert OAuth2ProviderFactory._is_provider_configured("github") is False

    def test_is_provider_configured_unknown_provider(self) -> None:
        """Test provider configuration check for unknown provider."""
        assert OAuth2ProviderFactory._is_provider_configured("unknown") is False

    def test_create_provider_github_success(self) -> None:
        """Test creating GitHub provider successfully."""
        with patch('app.integrations.oauth.factory.settings') as mock_settings:
            mock_settings.github_client_id = "test_client_id"
            mock_settings.github_client_secret = "test_client_secret"
            mock_settings.oauth_redirect_base_url = "http://localhost:8080/api/v1/oauth"

            provider = OAuth2ProviderFactory.create_provider("github")
            assert isinstance(provider, GitHubOAuth2Provider)

    def test_create_provider_unsupported(self) -> None:
        """Test creating unsupported provider raises error."""
        with pytest.raises(UnsupportedProviderError) as exc_info:
            OAuth2ProviderFactory.create_provider("unknown")

        assert "not supported" in str(exc_info.value)

    def test_create_provider_not_configured(self) -> None:
        """Test creating provider that exists but is not configured."""
        with patch('app.integrations.oauth.factory.settings') as mock_settings:
            mock_settings.github_client_id = ""
            mock_settings.github_client_secret = ""

            with pytest.raises(UnsupportedProviderError) as exc_info:
                OAuth2ProviderFactory.create_provider("github")

            assert "not configured" in str(exc_info.value)

    def test_get_provider_config_github(self) -> None:
        """Test getting GitHub provider configuration."""
        with patch('app.integrations.oauth.factory.settings') as mock_settings:
            mock_settings.github_client_id = "test_client_id"
            mock_settings.github_client_secret = "test_client_secret"
            mock_settings.oauth_redirect_base_url = "http://localhost:8080/api/v1/oauth"

            config = OAuth2ProviderFactory._get_provider_config("github")

            assert config.client_id == "test_client_id"
            assert config.client_secret == "test_client_secret"
            assert config.authorization_url == "https://github.com/login/oauth/authorize"
            assert config.token_url == "https://github.com/login/oauth/access_token"
            assert "repo" in config.scopes
            assert "user:email" in config.scopes

    def test_get_provider_config_unknown(self) -> None:
        """Test getting config for unknown provider raises error."""
        with pytest.raises(UnsupportedProviderError) as exc_info:
            OAuth2ProviderFactory._get_provider_config("unknown")

        assert "No configuration for provider" in str(exc_info.value)

    def test_register_provider(self) -> None:
        """Test registering a new provider."""
        # Mock a new provider class
        class TestProvider:
            pass

        # Register the provider
        OAuth2ProviderFactory.register_provider("test", TestProvider)

        # Check it was registered
        assert "test" in OAuth2ProviderFactory._providers
        assert OAuth2ProviderFactory._providers["test"] == TestProvider

        # Clean up
        del OAuth2ProviderFactory._providers["test"]