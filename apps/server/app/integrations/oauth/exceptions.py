"""OAuth2-specific exceptions."""


class OAuth2Error(Exception):
    """Base OAuth2 error."""

    pass


class UnsupportedProviderError(OAuth2Error):
    """Raised when provider is not supported."""

    pass


class OAuth2TokenExchangeError(OAuth2Error):
    """Raised when token exchange fails."""

    pass


class OAuth2RefreshError(OAuth2Error):
    """Raised when token refresh fails."""

    pass


class OAuth2ValidationError(OAuth2Error):
    """Raised when token validation fails."""

    pass


__all__ = [
    "OAuth2Error",
    "UnsupportedProviderError",
    "OAuth2TokenExchangeError",
    "OAuth2RefreshError",
    "OAuth2ValidationError",
]
