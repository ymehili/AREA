"""GitHub OAuth2 provider implementation."""

from __future__ import annotations

import httpx
import logging
from typing import Any, Dict
from urllib.parse import urlencode

from app.integrations.oauth.base import OAuth2Provider, OAuth2TokenSet
from app.integrations.oauth.exceptions import (
    OAuth2RefreshError,
    OAuth2TokenExchangeError,
    OAuth2ValidationError,
)

logger = logging.getLogger("area")


class GitHubOAuth2Provider(OAuth2Provider):
    """GitHub OAuth2 provider implementation."""

    @property
    def provider_name(self) -> str:
        return "github"

    def get_authorization_url(self, state: str, **kwargs) -> str:
        """Generate GitHub authorization URL."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": " ".join(self.config.scopes),
            "state": state,
            "response_type": "code",
        }
        return f"{self.config.authorization_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, **kwargs) -> OAuth2TokenSet:
        """Exchange authorization code for GitHub access token."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "AREA-App/1.0",
                    },
                    data={
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                        "code": code,
                        "redirect_uri": self.config.redirect_uri,
                    },
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    raise OAuth2TokenExchangeError(
                        f"GitHub OAuth error: {data['error']}"
                    )

                return OAuth2TokenSet(
                    access_token=data["access_token"],
                    scope=data.get("scope"),
                    token_type=data.get("token_type", "Bearer"),
                )
            except httpx.HTTPError as e:
                raise OAuth2TokenExchangeError(f"Failed to exchange code: {str(e)}")

    async def refresh_tokens(self, refresh_token: str) -> OAuth2TokenSet:
        """GitHub tokens don't expire, so this is a no-op."""
        raise OAuth2RefreshError("GitHub tokens do not support refresh")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get GitHub user information."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "AREA-App/1.0",
                    },
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to get user info: {str(e)}")

    async def validate_token(self, access_token: str) -> bool:
        """Validate GitHub access token."""
        try:
            await self.get_user_info(access_token)
            return True
        except OAuth2ValidationError:
            return False

    async def test_api_access(self, access_token: str) -> Dict[str, Any]:
        """Test GitHub API access with the token."""
        async with httpx.AsyncClient() as client:
            try:
                # Get user info and repositories
                user_response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "AREA-App/1.0",
                    },
                )
                user_response.raise_for_status()
                user_data = user_response.json()

                repos_response = await client.get(
                    "https://api.github.com/user/repos?per_page=5&sort=updated",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "AREA-App/1.0",
                    },
                )
                repos_response.raise_for_status()
                repos_data = repos_response.json()

                return {
                    "user": {
                        "login": user_data.get("login"),
                        "name": user_data.get("name"),
                        "email": user_data.get("email"),
                        "public_repos": user_data.get("public_repos"),
                        "followers": user_data.get("followers"),
                        "following": user_data.get("following"),
                    },
                    "recent_repositories": [
                        {
                            "name": repo.get("name"),
                            "full_name": repo.get("full_name"),
                            "private": repo.get("private"),
                            "description": repo.get("description"),
                            "updated_at": repo.get("updated_at"),
                        }
                        for repo in repos_data[:5]
                    ],
                }
            except httpx.HTTPError as e:
                raise OAuth2ValidationError(f"Failed to test API access: {str(e)}")

    async def revoke_token(self, access_token: str) -> bool:
        """Revoke a GitHub OAuth token.

        This uses the GitHub API to revoke the OAuth application grant,
        which invalidates all tokens for this user and application.

        Args:
            access_token: The access token to revoke

        Returns:
            True if revocation succeeded or token already revoked, False on actual errors
        """
        async with httpx.AsyncClient() as client:
            try:
                # Revoke the token using the GitHub API
                # https://docs.github.com/en/rest/apps/oauth-applications#delete-an-app-authorization
                response = await client.delete(
                    f"https://api.github.com/applications/{self.config.client_id}/grant",
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "AREA-App/1.0",
                    },
                    auth=(self.config.client_id, self.config.client_secret),
                    json={"access_token": access_token},
                )
                # 204 No Content means success
                response.raise_for_status()
                return True
            except httpx.HTTPStatusError as e:
                # 404 means token already revoked or doesn't exist - this is acceptable
                if e.response.status_code == 404:
                    logger.info("GitHub token already revoked or invalid")
                    return True
                # Other HTTP errors are real failures
                logger.error(
                    f"Failed to revoke GitHub token: HTTP {e.response.status_code}",
                    exc_info=True,
                )
                return False
            except httpx.HTTPError as e:
                # Network errors or other httpx errors
                logger.error(
                    f"Network error during GitHub token revocation: {e}", exc_info=True
                )
                return False


__all__ = ["GitHubOAuth2Provider"]
