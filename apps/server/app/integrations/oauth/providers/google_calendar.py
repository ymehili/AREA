"""Google Calendar OAuth2 provider implementation."""

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


class GoogleCalendarOAuth2Provider(OAuth2Provider):
    """Google Calendar OAuth2 provider implementation using Google OAuth."""

    @property
    def provider_name(self) -> str:
        return "google_calendar"

    def get_authorization_url(self, state: str, **kwargs) -> str:
        """Generate Google OAuth authorization URL for Calendar."""
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
        """Exchange authorization code for Google Calendar access and refresh tokens."""
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
                await response.raise_for_status()
                data = await response.json()

                if "error" in data:
                    raise OAuth2TokenExchangeError(f"Google Calendar OAuth error: {data['error']}")

                return OAuth2TokenSet(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_in=data.get("expires_in"),
                    scope=data.get("scope"),
                    token_type=data.get("token_type", "Bearer"),
                )
            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_json = await e.response.json()
                    error_detail = error_json.get("error", str(error_json))
                except Exception:
                    error_detail = str(e)
                raise OAuth2TokenExchangeError(f"Google Calendar OAuth error: {error_detail}") from e
            except httpx.HTTPError as e:
                raise OAuth2TokenExchangeError(f"Failed to exchange code: {str(e)}")

    async def refresh_tokens(self, refresh_token: str) -> OAuth2TokenSet:
        """Refresh Google Calendar access token using refresh token."""
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
                await response.raise_for_status()
                data = await response.json()

                if "error" in data:
                    raise OAuth2RefreshError(f"Google Calendar token refresh error: {data['error']}")

                return OAuth2TokenSet(
                    access_token=data["access_token"],
                    refresh_token=refresh_token,  # Keep the same refresh token
                    expires_in=data.get("expires_in"),
                    scope=data.get("scope"),
                    token_type=data.get("token_type", "Bearer"),
                )
            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_json = await e.response.json()
                    error_detail = error_json.get("error", str(error_json))
                except Exception:
                    error_detail = str(e)
                raise OAuth2RefreshError(f"Google Calendar token refresh error: {error_detail}") from e
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
                await response.raise_for_status()
                return await response.json()
            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_json = await e.response.json()
                    error_detail = error_json.get("error", str(error_json))
                except Exception:
                    error_detail = str(e)
                raise OAuth2ValidationError(f"Google Calendar OAuth error: {error_detail}") from e
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to get user info: {str(e)}")

    async def validate_token(self, access_token: str) -> bool:
        """Validate Google Calendar access token."""
        try:
            await self.get_user_info(access_token)
            return True
        except OAuth2ValidationError:
            return False

    async def test_api_access(self, access_token: str) -> Dict[str, Any]:
        """Test Google Calendar API access with the token."""
        async with httpx.AsyncClient() as client:
            try:
                # Get calendar list
                calendar_response = await client.get(
                    "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                await calendar_response.raise_for_status()
                calendar_data = await calendar_response.json()

                # Get primary calendar to verify full API access
                primary_response = await client.get(
                    "https://www.googleapis.com/calendar/v3/calendars/primary",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                await primary_response.raise_for_status()
                primary_data = await primary_response.json()

                return {
                    "primary_calendar": {
                        "id": primary_data.get("id"),
                        "summary": primary_data.get("summary"),
                        "timezone": primary_data.get("timeZone"),
                    },
                    "calendars": [
                        {
                            "id": cal.get("id"),
                            "summary": cal.get("summary"),
                            "primary": cal.get("primary", False),
                        }
                        for cal in calendar_data.get("items", [])[:5]
                    ],
                }
            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_json = await e.response.json()
                    error_detail = error_json.get("error", str(error_json))
                except Exception:
                    error_detail = str(e)
                raise OAuth2ValidationError(f"Google Calendar OAuth error: {error_detail}") from e
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to test API access: {str(e)}")


__all__ = ["GoogleCalendarOAuth2Provider"]
