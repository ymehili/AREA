"""Tests for GitHub plugin."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import HTTPStatusError, RequestError
import httpx

from app.integrations.simple_plugins.github_plugin import (
    create_issue_handler,
    add_comment_handler,
    close_issue_handler,
    add_label_handler,
    create_branch_handler,
    _get_github_access_token,
    _make_github_request,
)
from app.integrations.simple_plugins.exceptions import (
    GitHubAuthError,
    GitHubAPIError,
    GitHubConnectionError,
)
from app.models.area import Area
from app.models.user import User
from app.models.service_connection import ServiceConnection


class TestGitHubPlugin:
    """Test GitHub plugin functionality."""

    @pytest.fixture
    def mock_area(self):
        """Create a mock Area instance."""
        area = MagicMock(spec=Area)
        area.id = "test_area_id"
        area.user_id = "test_user_id"
        area.name = "Test Area"
        return area

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    def test_get_github_access_token_success(self, mock_area, mock_db):
        """Test getting GitHub access token successfully."""
        # Create a mock service connection
        mock_connection = MagicMock(spec=ServiceConnection)
        mock_connection.encrypted_access_token = "encrypted_token"
        
        with patch("app.integrations.simple_plugins.github_plugin.get_service_connection_by_user_and_service") as mock_get_conn:
            with patch("app.core.encryption.decrypt_token") as mock_decrypt:
                mock_get_conn.return_value = mock_connection
                mock_decrypt.return_value = "decrypted_token"

                token = _get_github_access_token(mock_area, mock_db)
                
                assert token == "decrypted_token"
                mock_get_conn.assert_called_once_with(mock_db, "test_user_id", "github")
                mock_decrypt.assert_called_once_with("encrypted_token")

    def test_get_github_access_token_no_connection(self, mock_area, mock_db):
        """Test getting GitHub access token when no connection exists."""
        with patch("app.integrations.simple_plugins.github_plugin.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.return_value = None

            with pytest.raises(GitHubConnectionError):
                _get_github_access_token(mock_area, mock_db)

    def test_get_github_access_token_no_token(self, mock_area, mock_db):
        """Test getting GitHub access token when encrypted token is None."""
        # Create a mock service connection
        mock_connection = MagicMock(spec=ServiceConnection)
        mock_connection.encrypted_access_token = None
        
        with patch("app.integrations.simple_plugins.github_plugin.get_service_connection_by_user_and_service") as mock_get_conn:
            with patch("app.core.encryption.decrypt_token") as mock_decrypt:
                mock_get_conn.return_value = mock_connection
                mock_decrypt.return_value = None

                with pytest.raises(GitHubAuthError):
                    _get_github_access_token(mock_area, mock_db)

    @pytest.mark.asyncio
    async def test_make_github_request_success(self):
        """Test making a successful GitHub API request."""
        mock_response_data = {"id": 1, "title": "Test Issue"}

        with patch("app.integrations.simple_plugins.github_plugin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_response.content = b"{}"

            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _make_github_request(
                "GET",
                "/repos/test/test_repo/issues/1",
                "test_token",
                params={"state": "open"}
            )

            if hasattr(result, '__await__'):
                result = await result
            assert result == mock_response_data
            mock_client.request.assert_called_once_with(
                method="GET",
                url="https://api.github.com/repos/test/test_repo/issues/1",
                headers={
                    "Authorization": "Bearer test_token",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "AREA-App/1.0",
                },
                json=None,
                params={"state": "open"},
                timeout=30.0,
            )

    @pytest.mark.asyncio
    async def test_make_github_request_with_data(self):
        """Test making a GitHub API request with JSON data."""
        mock_request_data = {"title": "New Issue", "body": "Issue description"}
        mock_response_data = {"id": 2, "title": "New Issue"}

        with patch("app.integrations.simple_plugins.github_plugin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            # Instead of returning a coroutine, we should mock the awaitable response values
            type(mock_response).raise_for_status = AsyncMock(return_value=None)
            type(mock_response).json = AsyncMock(return_value=mock_response_data)
            type(mock_response).content = b"{}"
            
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await _make_github_request(
                "POST",
                "/repos/test/test_repo/issues",
                "test_token",
                json_data=mock_request_data
            )

            if hasattr(result, '__await__'):
                result = await result
            assert result == mock_response_data
            mock_client.request.assert_called_once_with(
                method="POST",
                url="https://api.github.com/repos/test/test_repo/issues",
                headers={
                    "Authorization": "Bearer test_token",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "AREA-App/1.0",
                },
                json=mock_request_data,
                params=None,
                timeout=30.0,
            )

    @pytest.mark.asyncio
    async def test_make_github_request_http_status_error(self):
        """Test handling HTTP status error during GitHub API request."""
        mock_error_response = AsyncMock()
        mock_error_response.json.return_value = {"message": "Not Found"}
        mock_error_response.text = '{"message": "Not Found"}'
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request.side_effect = HTTPStatusError(
                "404 Client Error: Not Found for url: https://api.github.com/repos/test/test_repo/issues/999",
                request=MagicMock(),
                response=mock_error_response,
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(GitHubAPIError):
                await _make_github_request(
                    "GET",
                    "/repos/test/test_repo/issues/999",
                    "test_token"
                )

    @pytest.mark.asyncio
    async def test_make_github_request_http_error(self):
        """Test handling general HTTP error during GitHub API request."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request.side_effect = RequestError(
                "Connection error",
                request=MagicMock(),
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(GitHubAPIError):
                await _make_github_request(
                    "GET",
                    "/repos/test/test_repo/issues/1",
                    "test_token"
                )

    @pytest.mark.asyncio
    async def test_create_issue_handler_success(self, mock_area, mock_db):
        """Test creating a GitHub issue successfully."""
        params = {
            "repo_owner": "test_owner",
            "repo_name": "test_repo",
            "title": "Test Issue",
            "body": "Issue description",
            "labels": ["bug", "help wanted"],
            "assignees": ["user1", "user2"]
        }
        event = {}

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token:
            with patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_make_request:
                mock_get_token.return_value = "test_token"
                mock_make_request.return_value = {
                    "number": 1,
                    "html_url": "https://github.com/test_owner/test_repo/issues/1"
                }

                await create_issue_handler(mock_area, params, event, mock_db)

                mock_get_token.assert_called_once_with(mock_area, mock_db)
                mock_make_request.assert_called_once_with(
                    "POST",
                    "/repos/test_owner/test_repo/issues",
                    "test_token",
                    json_data={
                        "title": "Test Issue",
                        "body": "Issue description",
                        "labels": ["bug", "help wanted"],
                        "assignees": ["user1", "user2"]
                    }
                )

    @pytest.mark.asyncio
    async def test_create_issue_handler_missing_params(self, mock_area, mock_db):
        """Test creating a GitHub issue with missing required parameters."""
        params = {
            # Missing repo_owner, repo_name, and title
            "body": "Issue description"
        }
        event = {}

        with pytest.raises(ValueError) as exc_info:
            await create_issue_handler(mock_area, params, event, mock_db)
        
        assert "'repo_owner' and 'repo_name' parameters are required" in str(exc_info.value)

        params = {
            "repo_owner": "test_owner",
            "repo_name": "test_repo",
            # Missing title
            "body": "Issue description"
        }

        with pytest.raises(ValueError) as exc_info:
            await create_issue_handler(mock_area, params, event, mock_db)
        
        assert "'title' parameter is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_comment_handler_success(self, mock_area, mock_db):
        """Test adding a comment to a GitHub issue successfully."""
        params = {
            "repo_owner": "test_owner",
            "repo_name": "test_repo",
            "issue_number": 1,
            "body": "This is a comment"
        }
        event = {}

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token:
            with patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_make_request:
                mock_get_token.return_value = "test_token"
                mock_make_request.return_value = {
                    "id": 123,
                    "html_url": "https://github.com/test_owner/test_repo/issues/1#comment-123"
                }

                await add_comment_handler(mock_area, params, event, mock_db)

                mock_get_token.assert_called_once_with(mock_area, mock_db)
                mock_make_request.assert_called_once_with(
                    "POST",
                    "/repos/test_owner/test_repo/issues/1/comments",
                    "test_token",
                    json_data={"body": "This is a comment"}
                )

    @pytest.mark.asyncio
    async def test_add_comment_handler_missing_params(self, mock_area, mock_db):
        """Test adding a comment with missing required parameters."""
        params = {
            "repo_owner": "test_owner",
            "repo_name": "test_repo",
            # Missing issue_number and body
        }
        event = {}

        with pytest.raises(ValueError) as exc_info:
            await add_comment_handler(mock_area, params, event, mock_db)
        
        assert "'issue_number' is required" in str(exc_info.value)

        params = {
            "repo_owner": "test_owner",
            "repo_name": "test_repo",
            "issue_number": 1,
            # Missing body
        }

        with pytest.raises(ValueError) as exc_info:
            await add_comment_handler(mock_area, params, event, mock_db)
        
        assert "'body' parameter is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_close_issue_handler_success(self, mock_area, mock_db):
        """Test closing a GitHub issue successfully."""
        params = {
            "repo_owner": "test_owner",
            "repo_name": "test_repo",
            "issue_number": 1,
        }
        event = {}

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token:
            with patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_make_request:
                mock_get_token.return_value = "test_token"
                mock_make_request.return_value = {
                    "number": 1,
                    "html_url": "https://github.com/test_owner/test_repo/issues/1",
                    "state": "closed"
                }

                await close_issue_handler(mock_area, params, event, mock_db)

                mock_get_token.assert_called_once_with(mock_area, mock_db)
                mock_make_request.assert_called_once_with(
                    "PATCH",
                    "/repos/test_owner/test_repo/issues/1",
                    "test_token",
                    json_data={"state": "closed"}
                )

    @pytest.mark.asyncio
    async def test_add_label_handler_success(self, mock_area, mock_db):
        """Test adding labels to a GitHub issue successfully."""
        params = {
            "repo_owner": "test_owner",
            "repo_name": "test_repo",
            "issue_number": 1,
            "labels": ["bug", "priority:high"]
        }
        event = {}

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token:
            with patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_make_request:
                mock_get_token.return_value = "test_token"
                mock_make_request.return_value = [
                    {"name": "bug", "color": "e11d21"},
                    {"name": "priority:high", "color": "eb6420"}
                ]

                await add_label_handler(mock_area, params, event, mock_db)

                mock_get_token.assert_called_once_with(mock_area, mock_db)
                mock_make_request.assert_called_once_with(
                    "POST",
                    "/repos/test_owner/test_repo/issues/1/labels",
                    "test_token",
                    json_data={"labels": ["bug", "priority:high"]}
                )

    @pytest.mark.asyncio
    async def test_create_branch_handler_success(self, mock_area, mock_db):
        """Test creating a GitHub branch successfully."""
        params = {
            "repo_owner": "test_owner",
            "repo_name": "test_repo",
            "branch_name": "feature/new-feature",
            "from_branch": "main"
        }
        event = {}

        mock_repo_ref = {
            "object": {
                "sha": "abc123def456"
            }
        }
        mock_created_ref = {
            "ref": "refs/heads/feature/new-feature",
            "object": {
                "sha": "abc123def456"
            }
        }

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token:
            with patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_make_request:
                mock_get_token.return_value = "test_token"
                # First call: get source ref, second call: create new ref
                mock_make_request.side_effect = [mock_repo_ref, mock_created_ref]

                await create_branch_handler(mock_area, params, event, mock_db)

                # Check that _make_github_request was called twice
                assert mock_make_request.call_count == 2
                # First call to get source ref
                mock_make_request.assert_any_call(
                    "GET",
                    "/repos/test_owner/test_repo/git/ref/heads/main",
                    "test_token"
                )
                # Second call to create new ref
                mock_make_request.assert_any_call(
                    "POST",
                    "/repos/test_owner/test_repo/git/refs",
                    "test_token",
                    json_data={
                        "ref": "refs/heads/feature/new-feature",
                        "sha": "abc123def456"
                    }
                )