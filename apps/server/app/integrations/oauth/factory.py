"""Factory for creating OAuth2 providers."""

from __future__ import annotations

from typing import Dict, Type

from app.core.config import settings
from app.integrations.oauth.base import OAuth2Config, OAuth2Provider
from app.integrations.oauth.exceptions import UnsupportedProviderError
from app.integrations.oauth.providers.github import GitHubOAuth2Provider
from app.integrations.oauth.providers.google import GoogleOAuth2Provider


class OAuth2ProviderFactory:
    """Factory for creating OAuth2 providers."""

    _providers: Dict[str, Type[OAuth2Provider]] = {
        "github": GitHubOAuth2Provider,
        "gmail": GoogleOAuth2Provider,  # Gmail provider using Google OAuth
        # Future providers will be registered here
    }

    @classmethod
    def create_provider(cls, provider_name: str) -> OAuth2Provider:
        """Create OAuth2 provider instance."""
        if provider_name not in cls._providers:
            raise UnsupportedProviderError(f"Provider '{provider_name}' is not supported")

        if not cls._is_provider_configured(provider_name):
            raise UnsupportedProviderError(
                f"Provider '{provider_name}' is not configured. "
                f"Please set the required environment variables."
            )

        config = cls._get_provider_config(provider_name)
        provider_class = cls._providers[provider_name]
        return provider_class(config)

    @classmethod
    def _get_provider_config(cls, provider_name: str) -> OAuth2Config:
        """Get configuration for specific provider."""
        if provider_name == "github":
            return OAuth2Config(
                client_id=settings.github_client_id,
                client_secret=settings.github_client_secret,
                authorization_url="https://github.com/login/oauth/authorize",
                token_url="https://github.com/login/oauth/access_token",
                scopes=["repo", "user:email", "notifications"],
                redirect_uri=f"{settings.oauth_redirect_base_url.replace('/oauth', '')}/service-connections/callback/github",
            )
        
        if provider_name == "gmail":
            return OAuth2Config(
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                authorization_url="https://accounts.google.com/o/oauth2/auth",
                token_url="https://oauth2.googleapis.com/token",
                scopes=[
                    "https://www.googleapis.com/auth/gmail.readonly",  # Read emails
                    "https://www.googleapis.com/auth/gmail.send",      # Send emails
                    "https://www.googleapis.com/auth/gmail.modify",    # Modify labels (mark as read, etc.)
                    "https://www.googleapis.com/auth/userinfo.email", # Access email address
                    "https://www.googleapis.com/auth/userinfo.profile" # Access profile
                ],
                redirect_uri=f"{settings.oauth_redirect_base_url.replace('/oauth', '')}/service-connections/callback/gmail",
            )

        raise UnsupportedProviderError(f"No configuration for provider: {provider_name}")

    @classmethod
    def register_provider(cls, provider_name: str, provider_class: Type[OAuth2Provider]):
        """Register a new OAuth2 provider."""
        cls._providers[provider_name] = provider_class

    @classmethod
    def _is_provider_configured(cls, provider_name: str) -> bool:
        """Check if provider has required credentials configured."""
        if provider_name == "github":
            return bool(settings.github_client_id and settings.github_client_secret)
        
        if provider_name == "gmail":
            return bool(settings.google_client_id and settings.google_client_secret)

        return False

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported provider names that are properly configured."""
        return [
            provider_name
            for provider_name in cls._providers.keys()
            if cls._is_provider_configured(provider_name)
        ]


__all__ = ["OAuth2ProviderFactory"]