"""Tests for GitHub plugin handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
import httpx

from app.integrations.simple_plugins.github_plugin import (
    _get_github_access_token,
    _make_github_request,
    create_issue_handler,
    add_comment_handler,
    close_issue_handler,
    add_label_handler,
    create_branch_handler,
)
from app.integrations.simple_plugins.exceptions import (
    GitHubAuthError,
    GitHubAPIError,
    GitHubConnectionError,
)


class TestGitHubPlugin:
    """Test GitHub plugin functionality."""

    @pytest.mark.asyncio
    async def test_make_github_request_success(self):
        """Test successful GitHub API request."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": 123, "title": "Test Issue"}
        mock_response.content = b'{"id": 123}'

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await _make_github_request(
                "POST",
                "/repos/owner/repo/issues",
                "test_token",
                json_data={"title": "Test Issue"}
            )

            assert result == {"id": 123, "title": "Test Issue"}

    @pytest.mark.asyncio
    async def test_make_github_request_empty_response(self):
        """Test GitHub API request with empty response."""
        mock_response = Mock()
        mock_response.content = b''

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await _make_github_request(
                "DELETE",
                "/repos/owner/repo/issues/1",
                "test_token"
            )

            assert result == {}

    @pytest.mark.asyncio
    async def test_make_github_request_http_error(self):
        """Test GitHub API request with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            error = httpx.HTTPStatusError("Not Found", request=Mock(), response=mock_response)
            mock_client.request.side_effect = error
            mock_client_class.return_value = mock_client

            with pytest.raises(GitHubAPIError, match="GitHub API error"):
                await _make_github_request("GET", "/repos/owner/repo", "test_token")

    @pytest.mark.asyncio
    async def test_make_github_request_http_error_no_json(self):
        """Test GitHub API request with HTTP error and no JSON response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("No JSON")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            error = httpx.HTTPStatusError("Server Error", request=Mock(), response=mock_response)
            mock_client.request.side_effect = error
            mock_client_class.return_value = mock_client

            with pytest.raises(GitHubAPIError, match="GitHub API error"):
                await _make_github_request("GET", "/repos/owner/repo", "test_token")

    @pytest.mark.asyncio
    async def test_make_github_request_connection_error(self):
        """Test GitHub API request with connection error."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request.side_effect = httpx.ConnectError("Connection failed")
            mock_client_class.return_value = mock_client

            with pytest.raises(GitHubAPIError, match="Failed to connect to GitHub API"):
                await _make_github_request("GET", "/repos/owner/repo", "test_token")

    @pytest.mark.asyncio
    async def test_create_issue_handler_success(self):
        """Test successful issue creation."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "title": "Test Issue",
            "body": "Issue description",
            "labels": ["bug", "urgent"],
            "assignees": ["user1"]
        }
        event = {}
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.return_value = {"number": 42, "html_url": "https://github.com/testowner/testrepo/issues/42"}

            await create_issue_handler(area, params, event, mock_db)

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "/repos/testowner/testrepo/issues"
            assert call_args[1]["json_data"]["title"] == "Test Issue"
            assert call_args[1]["json_data"]["body"] == "Issue description"

    @pytest.mark.asyncio
    async def test_create_issue_handler_no_db(self):
        """Test issue creation without database session."""
        area = Mock()
        params = {"repo_owner": "owner", "repo_name": "repo", "title": "Test"}
        event = {}

        with pytest.raises(ValueError, match="Database session is required"):
            await create_issue_handler(area, params, event, None)

    @pytest.mark.asyncio
    async def test_create_issue_handler_missing_params(self):
        """Test issue creation with missing parameters."""
        area = Mock()
        area.id = "area-id"
        area.user_id = "user-id"
        mock_db = Mock()

        # Missing repo_owner
        params = {"repo_name": "testrepo", "title": "Test"}
        with pytest.raises(ValueError, match="'repo_owner' and 'repo_name' parameters are required"):
            await create_issue_handler(area, params, {}, mock_db)

        # Missing title
        params = {"repo_owner": "owner", "repo_name": "repo"}
        with pytest.raises(ValueError, match="'title' parameter is required"):
            await create_issue_handler(area, params, {}, mock_db)

    @pytest.mark.asyncio
    async def test_create_issue_handler_labels_as_string(self):
        """Test issue creation with labels as string."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "title": "Test Issue",
            "labels": "bug"  # String instead of list
        }
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.return_value = {"number": 42, "html_url": "https://github.com/testowner/testrepo/issues/42"}

            await create_issue_handler(area, params, {}, mock_db)

            call_args = mock_request.call_args
            assert call_args[1]["json_data"]["labels"] == ["bug"]

    @pytest.mark.asyncio
    async def test_add_comment_handler_success(self):
        """Test successful comment addition."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "issue_number": 42,
            "body": "Test comment"
        }
        event = {}
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.return_value = {"id": 123, "html_url": "https://github.com/testowner/testrepo/issues/42#comment-123"}

            await add_comment_handler(area, params, event, mock_db)

            call_args = mock_request.call_args
            assert call_args[0][1] == "/repos/testowner/testrepo/issues/42/comments"
            assert call_args[1]["json_data"]["body"] == "Test comment"

    @pytest.mark.asyncio
    async def test_add_comment_handler_from_event(self):
        """Test comment addition with issue_number from event."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "body": "Test comment"
        }
        event = {"github.issue_number": "42"}
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.return_value = {"id": 123}

            await add_comment_handler(area, params, event, mock_db)

            call_args = mock_request.call_args
            assert "/issues/42/comments" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_add_comment_handler_invalid_issue_number(self):
        """Test comment addition with invalid issue number."""
        area = Mock()
        area.id = "area-id"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "issue_number": "not-a-number",
            "body": "Test"
        }
        mock_db = Mock()

        with pytest.raises(ValueError, match="Invalid issue_number"):
            await add_comment_handler(area, params, {}, mock_db)

    @pytest.mark.asyncio
    async def test_add_comment_handler_missing_params(self):
        """Test comment addition with missing parameters."""
        area = Mock()
        area.id = "area-id"
        area.user_id = "user-id"
        mock_db = Mock()

        # Missing issue_number
        params = {"repo_owner": "owner", "repo_name": "repo", "body": "Test"}
        with pytest.raises(ValueError, match="'issue_number' is required"):
            await add_comment_handler(area, params, {}, mock_db)

        # Missing body
        params = {"repo_owner": "owner", "repo_name": "repo", "issue_number": 42}
        with pytest.raises(ValueError, match="'body' parameter is required"):
            await add_comment_handler(area, params, {}, mock_db)

    @pytest.mark.asyncio
    async def test_close_issue_handler_success(self):
        """Test successful issue closing."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "issue_number": 42
        }
        event = {}
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.return_value = {"state": "closed", "html_url": "https://github.com/testowner/testrepo/issues/42"}

            await close_issue_handler(area, params, event, mock_db)

            call_args = mock_request.call_args
            assert call_args[0][0] == "PATCH"
            assert call_args[0][1] == "/repos/testowner/testrepo/issues/42"
            assert call_args[1]["json_data"]["state"] == "closed"

    @pytest.mark.asyncio
    async def test_close_issue_handler_from_event(self):
        """Test issue closing with issue_number from event."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo"
        }
        event = {"github.issue_number": 42}
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.return_value = {"state": "closed"}

            await close_issue_handler(area, params, event, mock_db)

            call_args = mock_request.call_args
            assert "/issues/42" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_add_label_handler_success(self):
        """Test successful label addition."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "issue_number": 42,
            "labels": ["bug", "urgent"]
        }
        event = {}
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.return_value = [{"name": "bug"}, {"name": "urgent"}]

            await add_label_handler(area, params, event, mock_db)

            call_args = mock_request.call_args
            assert call_args[0][1] == "/repos/testowner/testrepo/issues/42/labels"
            assert call_args[1]["json_data"]["labels"] == ["bug", "urgent"]

    @pytest.mark.asyncio
    async def test_add_label_handler_string_label(self):
        """Test label addition with label as string."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "issue_number": 42,
            "labels": "bug"  # String instead of list
        }
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.return_value = [{"name": "bug"}]

            await add_label_handler(area, params, {}, mock_db)

            call_args = mock_request.call_args
            assert call_args[1]["json_data"]["labels"] == ["bug"]

    @pytest.mark.asyncio
    async def test_add_label_handler_missing_labels(self):
        """Test label addition with missing labels parameter."""
        area = Mock()
        area.id = "area-id"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "owner",
            "repo_name": "repo",
            "issue_number": 42
        }
        mock_db = Mock()

        with pytest.raises(ValueError, match="'labels' parameter is required"):
            await add_label_handler(area, params, {}, mock_db)

    @pytest.mark.asyncio
    async def test_create_branch_handler_success(self):
        """Test successful branch creation."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "branch_name": "feature-branch",
            "from_branch": "main"
        }
        event = {}
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.side_effect = [
                {"object": {"sha": "abc123"}},  # GET ref response
                {"ref": "refs/heads/feature-branch"}  # POST ref response
            ]

            await create_branch_handler(area, params, event, mock_db)

            assert mock_request.call_count == 2
            # Verify GET request for source branch
            assert mock_request.call_args_list[0][0][0] == "GET"
            assert "heads/main" in mock_request.call_args_list[0][0][1]
            # Verify POST request to create branch
            assert mock_request.call_args_list[1][0][0] == "POST"
            assert mock_request.call_args_list[1][1]["json_data"]["ref"] == "refs/heads/feature-branch"
            assert mock_request.call_args_list[1][1]["json_data"]["sha"] == "abc123"

    @pytest.mark.asyncio
    async def test_create_branch_handler_default_from_branch(self):
        """Test branch creation with default from_branch."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "branch_name": "feature-branch"
            # from_branch not specified, should default to "main"
        }
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.side_effect = [
                {"object": {"sha": "abc123"}},
                {"ref": "refs/heads/feature-branch"}
            ]

            await create_branch_handler(area, params, {}, mock_db)

            # Verify it uses "main" as default
            assert "heads/main" in mock_request.call_args_list[0][0][1]

    @pytest.mark.asyncio
    async def test_create_branch_handler_missing_params(self):
        """Test branch creation with missing parameters."""
        area = Mock()
        area.id = "area-id"
        area.user_id = "user-id"
        mock_db = Mock()

        # Missing branch_name
        params = {"repo_owner": "owner", "repo_name": "repo"}
        with pytest.raises(ValueError, match="'branch_name' parameter is required"):
            await create_branch_handler(area, params, {}, mock_db)

    @pytest.mark.asyncio
    async def test_create_issue_handler_api_error(self):
        """Test issue creation with API error."""
        area = Mock()
        area.id = "area-id"
        area.name = "Test Area"
        area.user_id = "user-id"
        
        params = {
            "repo_owner": "testowner",
            "repo_name": "testrepo",
            "title": "Test Issue"
        }
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.github_plugin._get_github_access_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.github_plugin._make_github_request") as mock_request:

            mock_get_token.return_value = "test_token"
            mock_request.side_effect = GitHubAPIError("API Error")

            with pytest.raises(GitHubAPIError):
                await create_issue_handler(area, params, {}, mock_db)

