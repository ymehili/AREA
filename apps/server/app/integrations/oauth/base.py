"""Abstract base classes for OAuth2 providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OAuth2Config:
    """OAuth2 configuration for a provider."""

    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    scopes: List[str]
    redirect_uri: str


@dataclass
class OAuth2TokenSet:
    """OAuth2 token response."""

    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    scope: Optional[str] = None
    token_type: str = "Bearer"


class OAuth2Provider(ABC):
    """Abstract base class for OAuth2 providers."""

    def __init__(self, config: OAuth2Config):
        self.config = config

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier."""
        pass

    @abstractmethod
    def get_authorization_url(self, state: str, **kwargs) -> str:
        """Generate authorization URL."""
        pass

    @abstractmethod
    async def exchange_code_for_tokens(self, code: str, **kwargs) -> OAuth2TokenSet:
        """Exchange authorization code for tokens."""
        pass

    @abstractmethod
    async def refresh_tokens(self, refresh_token: str) -> OAuth2TokenSet:
        """Refresh access token using refresh token."""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from the provider."""
        pass

    @abstractmethod
    async def validate_token(self, access_token: str) -> bool:
        """Validate if token is still valid."""
        pass


__all__ = ["OAuth2Config", "OAuth2TokenSet", "OAuth2Provider"]