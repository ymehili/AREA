"""Google OAuth2 provider implementation supporting Gmail API."""

from __future__ import annotations

import base64
import email
import httpx
import quopri
from typing import Any, Dict
from urllib.parse import urlencode

from app.integrations.oauth.base import OAuth2Provider, OAuth2TokenSet
from app.integrations.oauth.exceptions import (
    OAuth2RefreshError,
    OAuth2TokenExchangeError,
    OAuth2ValidationError,
)


class GoogleOAuth2Provider(OAuth2Provider):
    """Google OAuth2 provider implementation supporting Gmail API."""

    @property
    def provider_name(self) -> str:
        return "gmail"

    def get_authorization_url(self, state: str, **kwargs) -> str:
        """Generate Google authorization URL with Gmail scopes."""
        # Merge additional scopes from kwargs if provided
        scopes = self.config.scopes.copy()
        if "scopes" in kwargs:
            scopes.extend([scope for scope in kwargs["scopes"] if scope not in scopes])
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "response_type": "code",
            "access_type": "offline",  # Required to receive refresh token
            "prompt": "consent"  # Ensure refresh token is provided
        }
        return f"{self.config.authorization_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, **kwargs) -> OAuth2TokenSet:
        """Exchange authorization code for Google access and refresh tokens."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    headers={"Accept": "application/json"},
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
                    raise OAuth2TokenExchangeError(f"Google OAuth error: {data['error']}")

                return OAuth2TokenSet(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),  # May not be present on subsequent exchanges
                    expires_in=data.get("expires_in"),
                    scope=data.get("scope"),
                    token_type=data.get("token_type", "Bearer"),
                )
            except httpx.HTTPError as e:
                raise OAuth2TokenExchangeError(f"Failed to exchange code: {str(e)}")

    async def refresh_tokens(self, refresh_token: str) -> OAuth2TokenSet:
        """Refresh access token using refresh token."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    headers={"Accept": "application/json"},
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
                    raise OAuth2RefreshError(f"Google token refresh error: {data['error']}")

                return OAuth2TokenSet(
                    access_token=data["access_token"],
                    refresh_token=refresh_token,  # Refresh token is usually not updated
                    expires_in=data.get("expires_in"),
                    scope=data.get("scope"),
                    token_type=data.get("token_type", "Bearer"),
                )
            except httpx.HTTPError as e:
                raise OAuth2RefreshError(f"Failed to refresh tokens: {str(e)}")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Google user information using People API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://people.googleapis.com/v1/people/me?personFields=names,emailAddresses,photos",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to get user info: {str(e)}")

    async def validate_token(self, access_token: str) -> bool:
        """Validate Google access token by attempting to access user info."""
        try:
            await self.get_user_info(access_token)
            return True
        except OAuth2ValidationError:
            return False

    async def get_gmail_profile(self, access_token: str) -> Dict[str, Any]:
        """Get Gmail profile information."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://www.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to get Gmail profile: {str(e)}")

    async def list_gmail_messages(self, access_token: str, query: str = "", max_results: int = 100) -> Dict[str, Any]:
        """List Gmail messages based on query."""
        async with httpx.AsyncClient() as client:
            try:
                url = f"https://www.googleapis.com/gmail/v1/users/me/messages?maxResults={max_results}"
                if query:
                    url += f"&q={query}"
                
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to list Gmail messages: {str(e)}")

    async def get_gmail_message(self, access_token: str, message_id: str) -> Dict[str, Any]:
        """Get a specific Gmail message."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://www.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to get Gmail message: {str(e)}")

    async def send_gmail_message(self, access_token: str, raw_message: str) -> Dict[str, Any]:
        """Send a Gmail message."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://www.googleapis.com/gmail/v1/users/me/messages/send",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json={"raw": raw_message}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to send Gmail message: {str(e)}")

    async def modify_gmail_message(self, access_token: str, message_id: str, add_labels: list[str] = None, remove_labels: list[str] = None) -> Dict[str, Any]:
        """Modify a Gmail message by adding/removing labels."""
        async with httpx.AsyncClient() as client:
            try:
                body = {}
                if add_labels:
                    body["addLabelIds"] = add_labels
                if remove_labels:
                    body["removeLabelIds"] = remove_labels
                
                response = await client.post(
                    f"https://www.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=body
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to modify Gmail message: {str(e)}")

    def create_raw_email(self, to: str, subject: str, body: str, cc: str = None, bcc: str = None) -> str:
        """Create a raw email message in MIME format, base64url encoded."""
        import email.mime.text
        import email.mime.multipart
        import base64
        
        msg = email.mime.multipart.MIMEMultipart()
        msg['to'] = to
        msg['subject'] = subject
        
        if cc:
            msg['cc'] = cc
        if bcc:
            msg['bcc'] = bcc
            
        msg.attach(email.mime.text.MIMEText(body, 'plain'))
        
        # Convert to string and encode
        raw = msg.as_string()
        raw_encoded = base64.urlsafe_b64encode(raw.encode('utf-8')).decode('utf-8')
        
        return raw_encoded


__all__ = ["GoogleOAuth2Provider"]