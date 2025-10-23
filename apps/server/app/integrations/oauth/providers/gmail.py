"""Gmail OAuth2 provider implementation."""

from __future__ import annotations

import httpx
from typing import Any, Dict
from urllib.parse import urlencode

from app.integrations.oauth.base import OAuth2Provider, OAuth2TokenSet
from app.integrations.oauth.exceptions import (
    OAuth2RefreshError,
    OAuth2TokenExchangeError,
    OAuth2ValidationError,
)


class GmailOAuth2Provider(OAuth2Provider):
    """Gmail OAuth2 provider implementation using Google OAuth."""

    @property
    def provider_name(self) -> str:
        return "gmail"

    def get_authorization_url(self, state: str, **kwargs) -> str:
        """Generate Google OAuth authorization URL for Gmail."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
            "response_type": "code",
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
        }
        return f"{self.config.authorization_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, **kwargs) -> OAuth2TokenSet:
        """Exchange authorization code for Gmail access and refresh tokens."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    headers={
                        "Accept": "application/json",
                    },
                    data={
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                        "code": code,
                        "redirect_uri": self.config.redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    raise OAuth2TokenExchangeError(
                        f"Gmail OAuth error: {data['error']}"
                    )

                return OAuth2TokenSet(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_in=data.get("expires_in"),
                    scope=data.get("scope"),
                    token_type=data.get("token_type", "Bearer"),
                )
            except httpx.HTTPError as e:
                raise OAuth2TokenExchangeError(f"Failed to exchange code: {str(e)}")

    async def refresh_tokens(self, refresh_token: str) -> OAuth2TokenSet:
        """Refresh Gmail access token using refresh token."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    headers={
                        "Accept": "application/json",
                    },
                    data={
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    raise OAuth2RefreshError(
                        f"Gmail token refresh error: {data['error']}"
                    )

                return OAuth2TokenSet(
                    access_token=data["access_token"],
                    refresh_token=refresh_token,  # Keep the same refresh token
                    expires_in=data.get("expires_in"),
                    scope=data.get("scope"),
                    token_type=data.get("token_type", "Bearer"),
                )
            except httpx.HTTPError as e:
                raise OAuth2RefreshError(f"Failed to refresh token: {str(e)}")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Google user information."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to get user info: {str(e)}")

    async def validate_token(self, access_token: str) -> bool:
        """Validate Gmail access token."""
        try:
            await self.get_user_info(access_token)
            return True
        except OAuth2ValidationError:
            return False

    async def test_api_access(self, access_token: str) -> Dict[str, Any]:
        """Test Gmail API access with the token."""
        async with httpx.AsyncClient() as client:
            try:
                # Get user profile
                profile_response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                profile_response.raise_for_status()
                profile_data = profile_response.json()

                # Get labels to verify full API access
                labels_response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/labels",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                labels_response.raise_for_status()
                labels_data = labels_response.json()

                return {
                    "profile": {
                        "email": profile_data.get("emailAddress"),
                        "messages_total": profile_data.get("messagesTotal"),
                        "threads_total": profile_data.get("threadsTotal"),
                    },
                    "labels": [
                        {
                            "id": label.get("id"),
                            "name": label.get("name"),
                            "type": label.get("type"),
                        }
                        for label in labels_data.get("labels", [])[:10]
                    ],
                }
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to test API access: {str(e)}")


__all__ = ["GmailOAuth2Provider"]
