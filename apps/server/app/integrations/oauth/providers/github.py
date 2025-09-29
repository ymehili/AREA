"""GitHub OAuth2 provider implementation."""

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
                    raise OAuth2TokenExchangeError(f"GitHub OAuth error: {data['error']}")

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


__all__ = ["GitHubOAuth2Provider"]