"""Discord OAuth2 provider implementation."""

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


class DiscordOAuth2Provider(OAuth2Provider):
    """Discord OAuth2 provider implementation."""

    @property
    def provider_name(self) -> str:
        return "discord"

    def get_authorization_url(self, state: str, **kwargs) -> str:
        """Generate Discord authorization URL with bot permissions."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
            "response_type": "code",
            # Bot permissions:
            # 16 (Manage Channels) + 2048 (Send Messages) + 65536 (Read Message History) + 1024 (View Channels)
            # = 68624 (permissions for creating channels and sending messages)
            "permissions": "68624",
        }
        return f"{self.config.authorization_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, **kwargs) -> OAuth2TokenSet:
        """Exchange authorization code for Discord access token."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.config.redirect_uri,
                    },
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    raise OAuth2TokenExchangeError(f"Discord OAuth error: {data['error']}")

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
        """Refresh Discord access token using refresh token."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
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
                    raise OAuth2RefreshError(f"Discord token refresh error: {data['error']}")

                return OAuth2TokenSet(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),  # Use new or keep old
                    expires_in=data.get("expires_in"),
                    scope=data.get("scope"),
                    token_type=data.get("token_type", "Bearer"),
                )
            except httpx.HTTPError as e:
                raise OAuth2RefreshError(f"Failed to refresh token: {str(e)}")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Discord user information."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://discord.com/api/v10/users/@me",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to get user info: {str(e)}")

    async def validate_token(self, access_token: str) -> bool:
        """Validate Discord access token."""
        try:
            await self.get_user_info(access_token)
            return True
        except OAuth2ValidationError:
            return False

    async def test_api_access(self, access_token: str) -> Dict[str, Any]:
        """Test Discord API access with the token."""
        async with httpx.AsyncClient() as client:
            try:
                # Get user info
                user_response = await client.get(
                    "https://discord.com/api/v10/users/@me",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                user_response.raise_for_status()
                user_data = user_response.json()

                # Get user's guilds (servers)
                guilds_response = await client.get(
                    "https://discord.com/api/v10/users/@me/guilds",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                guilds_response.raise_for_status()
                guilds_data = guilds_response.json()

                return {
                    "user": {
                        "id": user_data.get("id"),
                        "username": user_data.get("username"),
                        "discriminator": user_data.get("discriminator"),
                        "global_name": user_data.get("global_name"),
                        "email": user_data.get("email"),
                        "verified": user_data.get("verified"),
                        "avatar": user_data.get("avatar"),
                    },
                    "guilds": [
                        {
                            "id": guild.get("id"),
                            "name": guild.get("name"),
                            "icon": guild.get("icon"),
                            "owner": guild.get("owner"),
                            "permissions": guild.get("permissions"),
                        }
                        for guild in guilds_data[:10]
                    ],
                    "guild_count": len(guilds_data),
                }
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to test API access: {str(e)}")


__all__ = ["DiscordOAuth2Provider"]
