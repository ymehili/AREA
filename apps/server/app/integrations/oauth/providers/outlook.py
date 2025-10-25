"""Outlook OAuth2 provider implementation using Microsoft identity platform."""

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


class OutlookOAuth2Provider(OAuth2Provider):
    """Outlook OAuth2 provider implementation using Microsoft identity platform.
    
    Uses Microsoft Graph API to access Outlook email functionality.
    Authentication flow follows OAuth 2.0 authorization code grant.
    """

    @property
    def provider_name(self) -> str:
        return "outlook"

    def get_authorization_url(self, state: str, **kwargs) -> str:
        """Generate Microsoft OAuth authorization URL for Outlook.
        
        Args:
            state: CSRF protection state parameter
            **kwargs: Additional parameters (not used)
            
        Returns:
            Authorization URL string
        """
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
            "response_type": "code",
            "response_mode": "query",
            # Ensures we get a refresh token
            "prompt": "consent",
        }
        return f"{self.config.authorization_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, **kwargs) -> OAuth2TokenSet:
        """Exchange authorization code for Outlook access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth callback
            **kwargs: Additional parameters (not used)
            
        Returns:
            OAuth2TokenSet containing access and refresh tokens
            
        Raises:
            OAuth2TokenExchangeError: If token exchange fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
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
                    error_desc = data.get("error_description", data["error"])
                    raise OAuth2TokenExchangeError(f"Outlook OAuth error: {error_desc}")

                return OAuth2TokenSet(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_in=data.get("expires_in"),
                    scope=data.get("scope"),
                    token_type=data.get("token_type", "Bearer"),
                )
            except httpx.HTTPError as e:
                raise OAuth2TokenExchangeError(
                    f"Failed to exchange code for Outlook tokens: {str(e)}"
                ) from e

    async def refresh_tokens(self, refresh_token: str) -> OAuth2TokenSet:
        """Refresh Outlook access token using refresh token.
        
        Args:
            refresh_token: Refresh token obtained during initial authorization
            
        Returns:
            OAuth2TokenSet with new access token
            
        Raises:
            OAuth2RefreshError: If token refresh fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    headers={
                        "Accept": "application/json",
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
                    error_desc = data.get("error_description", data["error"])
                    raise OAuth2RefreshError(f"Outlook token refresh error: {error_desc}")

                # Microsoft may return a new refresh token, or keep the old one
                return OAuth2TokenSet(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),
                    expires_in=data.get("expires_in"),
                    scope=data.get("scope"),
                    token_type=data.get("token_type", "Bearer"),
                )
            except httpx.HTTPError as e:
                raise OAuth2RefreshError(
                    f"Failed to refresh Outlook token: {str(e)}"
                ) from e

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Microsoft user information via Graph API.
        
        Args:
            access_token: Valid access token
            
        Returns:
            Dictionary containing user information (id, email, displayName, etc.)
            
        Raises:
            OAuth2ValidationError: If user info retrieval fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(
                    f"Failed to get Outlook user info: {str(e)}"
                ) from e

    async def validate_token(self, access_token: str) -> bool:
        """Validate Outlook access token by attempting to retrieve user info.
        
        Args:
            access_token: Token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            await self.get_user_info(access_token)
            return True
        except OAuth2ValidationError:
            return False

    async def test_api_access(self, access_token: str) -> Dict[str, Any]:
        """Test Outlook/Microsoft Graph API access with the token.
        
        Verifies that the token has proper permissions by fetching:
        - User profile
        - Mail folders
        - Recent messages count
        
        Args:
            access_token: Valid access token
            
        Returns:
            Dictionary with user profile and mailbox information
            
        Raises:
            OAuth2ValidationError: If API access test fails
        """
        async with httpx.AsyncClient() as client:
            try:
                # Get user profile
                user_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                user_response.raise_for_status()
                user_data = user_response.json()

                # Get mail folders to verify mail access
                folders_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me/mailFolders",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                folders_response.raise_for_status()
                folders_data = folders_response.json()

                # Get message count from inbox
                inbox_response = await client.get(
                    "https://graph.microsoft.com/v1.0/me/mailFolders/inbox",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                inbox_response.raise_for_status()
                inbox_data = inbox_response.json()

                return {
                    "profile": {
                        "id": user_data.get("id"),
                        "email": user_data.get("mail") or user_data.get("userPrincipalName"),
                        "displayName": user_data.get("displayName"),
                        "givenName": user_data.get("givenName"),
                        "surname": user_data.get("surname"),
                    },
                    "mailbox": {
                        "inbox_total_items": inbox_data.get("totalItemCount"),
                        "inbox_unread_items": inbox_data.get("unreadItemCount"),
                    },
                    "folders": [
                        {
                            "id": folder.get("id"),
                            "displayName": folder.get("displayName"),
                            "totalItemCount": folder.get("totalItemCount"),
                            "unreadItemCount": folder.get("unreadItemCount"),
                        }
                        for folder in folders_data.get("value", [])[:10]
                    ],
                }
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(
                    f"Failed to test Outlook API access: {str(e)}"
                ) from e


__all__ = ["OutlookOAuth2Provider"]
