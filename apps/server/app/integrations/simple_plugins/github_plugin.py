"""GitHub plugin for AREA - Implements repository automation actions and reactions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

import httpx

from app.db.session import SessionLocal
from app.services.service_connections import get_service_connection_by_user_and_service
from app.integrations.simple_plugins.exceptions import (
    GitHubAuthError,
    GitHubAPIError,
    GitHubConnectionError,
)

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


def _get_github_access_token(area: Area, db=None) -> str:
    """Get GitHub access token for a user.

    Args:
        area: The Area containing user_id
        db: Database session (optional, will create if not provided)

    Returns:
        GitHub access token string

    Raises:
        GitHubConnectionError: If service connection not found
        GitHubAuthError: If authentication fails
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Get service connection for GitHub
        connection = get_service_connection_by_user_and_service(db, area.user_id, "github")
        if not connection:
            raise GitHubConnectionError("GitHub service connection not found. Please connect your GitHub account.")

        # Decrypt access token
        from app.core.encryption import decrypt_token
        access_token = decrypt_token(connection.encrypted_access_token)

        if not access_token:
            raise GitHubAuthError("GitHub access token is invalid or expired.")

        return access_token
    finally:
        if close_db:
            db.close()


def _make_github_request(
    method: str,
    endpoint: str,
    access_token: str,
    json_data: dict = None,
    params: dict = None,
) -> dict:
    """Make an authenticated request to GitHub API (synchronous).

    Args:
        method: HTTP method (GET, POST, PATCH, etc.)
        endpoint: API endpoint (e.g., "/repos/{owner}/{repo}/issues")
        access_token: GitHub access token
        json_data: JSON body for POST/PATCH requests
        params: Query parameters

    Returns:
        Response JSON as dictionary

    Raises:
        GitHubAPIError: If the API request fails
    """
    url = f"{GITHUB_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "AREA-App/1.0",
    }

    with httpx.Client() as client:
        try:
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_json = e.response.json()
                error_detail = error_json.get("message", str(e))
            except Exception:
                error_detail = str(e)
            raise GitHubAPIError(f"GitHub API error: {error_detail}") from e
        except httpx.HTTPError as e:
            raise GitHubAPIError(f"Failed to connect to GitHub API: {str(e)}") from e


def create_issue_handler(area: Area, params: dict, event: dict) -> None:
    """Create a new issue in a GitHub repository.

    Args:
        area: The Area being executed
        params: Action parameters with 'repo_owner', 'repo_name', 'title', 'body', optional 'labels', 'assignees'
        event: Event data from trigger
    """
    try:
        # Extract parameters
        repo_owner = params.get("repo_owner")
        repo_name = params.get("repo_name")
        title = params.get("title")
        body = params.get("body", "")
        labels = params.get("labels", [])
        assignees = params.get("assignees", [])

        logger.info(
            "Starting GitHub create_issue action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "title": title,
                "params": params,
            },
        )

        if not repo_owner or not repo_name:
            raise ValueError("'repo_owner' and 'repo_name' parameters are required for create_issue action")
        if not title:
            raise ValueError("'title' parameter is required for create_issue action")

        # Get GitHub access token
        access_token = _get_github_access_token(area)

        # Prepare issue data
        issue_data = {
            "title": title,
            "body": body,
        }
        if labels:
            issue_data["labels"] = labels if isinstance(labels, list) else [labels]
        if assignees:
            issue_data["assignees"] = assignees if isinstance(assignees, list) else [assignees]

        # Create issue via GitHub API
        endpoint = f"/repos/{repo_owner}/{repo_name}/issues"
        result = _make_github_request("POST", endpoint, access_token, json_data=issue_data)

        logger.info(
            "GitHub issue created successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "issue_number": result.get("number"),
                "issue_url": result.get("html_url"),
                "title": title,
            }
        )
    except Exception as e:
        logger.error(
            "Error creating GitHub issue",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


def add_comment_handler(area: Area, params: dict, event: dict) -> None:
    """Add a comment to a GitHub issue or pull request.

    Args:
        area: The Area being executed
        params: Action parameters with 'repo_owner', 'repo_name', 'issue_number', 'body'
        event: Event data from trigger
    """

    try:
        # Extract parameters
        repo_owner = params.get("repo_owner")
        repo_name = params.get("repo_name")
        issue_number = params.get("issue_number")
        body = params.get("body")

        # Try to get issue_number from event if not in params
        if not issue_number:
            issue_number = event.get("github.issue_number") or event.get("github.pull_request_number")

        logger.info(
            "Starting GitHub add_comment action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "issue_number": issue_number,
                "params": params,
            },
        )

        if not repo_owner or not repo_name:
            raise ValueError("'repo_owner' and 'repo_name' parameters are required for add_comment action")
        if not issue_number:
            raise ValueError("'issue_number' is required. Use {{github.issue_number}} from trigger or provide it.")
        if not body:
            raise ValueError("'body' parameter is required for add_comment action")

        # Get GitHub access token
        access_token = _get_github_access_token(area)

        # Add comment via GitHub API
        endpoint = f"/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
        comment_data = {"body": body}
        result = _make_github_request("POST", endpoint, access_token, json_data=comment_data)

        logger.info(
            "GitHub comment added successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "issue_number": issue_number,
                "comment_id": result.get("id"),
                "comment_url": result.get("html_url"),
            }
        )
    except Exception as e:
        logger.error(
            "Error adding GitHub comment",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


def close_issue_handler(area: Area, params: dict, event: dict) -> None:
    """Close a GitHub issue.

    Args:
        area: The Area being executed
        params: Action parameters with 'repo_owner', 'repo_name', 'issue_number'
        event: Event data from trigger
    """

    try:
        # Extract parameters
        repo_owner = params.get("repo_owner")
        repo_name = params.get("repo_name")
        issue_number = params.get("issue_number")

        # Try to get issue_number from event if not in params
        if not issue_number:
            issue_number = event.get("github.issue_number")

        logger.info(
            "Starting GitHub close_issue action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "issue_number": issue_number,
                "params": params,
            },
        )

        if not repo_owner or not repo_name:
            raise ValueError("'repo_owner' and 'repo_name' parameters are required for close_issue action")
        if not issue_number:
            raise ValueError("'issue_number' is required. Use {{github.issue_number}} from trigger or provide it.")

        # Get GitHub access token
        access_token = _get_github_access_token(area)

        # Close issue via GitHub API
        endpoint = f"/repos/{repo_owner}/{repo_name}/issues/{issue_number}"
        issue_data = {"state": "closed"}
        result = _make_github_request("PATCH", endpoint, access_token, json_data=issue_data)

        logger.info(
            "GitHub issue closed successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "issue_number": issue_number,
                "issue_url": result.get("html_url"),
            }
        )
    except Exception as e:
        logger.error(
            "Error closing GitHub issue",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


def add_label_handler(area: Area, params: dict, event: dict) -> None:
    """Add labels to a GitHub issue or pull request.

    Args:
        area: The Area being executed
        params: Action parameters with 'repo_owner', 'repo_name', 'issue_number', 'labels'
        event: Event data from trigger
    """

    try:
        # Extract parameters
        repo_owner = params.get("repo_owner")
        repo_name = params.get("repo_name")
        issue_number = params.get("issue_number")
        labels = params.get("labels", [])

        # Try to get issue_number from event if not in params
        if not issue_number:
            issue_number = event.get("github.issue_number") or event.get("github.pull_request_number")

        logger.info(
            "Starting GitHub add_label action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "issue_number": issue_number,
                "labels": labels,
                "params": params,
            },
        )

        if not repo_owner or not repo_name:
            raise ValueError("'repo_owner' and 'repo_name' parameters are required for add_label action")
        if not issue_number:
            raise ValueError("'issue_number' is required. Use {{github.issue_number}} from trigger or provide it.")
        if not labels:
            raise ValueError("'labels' parameter is required for add_label action")

        # Ensure labels is a list
        if isinstance(labels, str):
            labels = [labels]

        # Get GitHub access token
        access_token = _get_github_access_token(area)

        # Add labels via GitHub API
        endpoint = f"/repos/{repo_owner}/{repo_name}/issues/{issue_number}/labels"
        labels_data = {"labels": labels}
        result = _make_github_request("POST", endpoint, access_token, json_data=labels_data)

        logger.info(
            "GitHub labels added successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "issue_number": issue_number,
                "labels_added": labels,
            }
        )
    except Exception as e:
        logger.error(
            "Error adding GitHub labels",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


def create_branch_handler(area: Area, params: dict, event: dict) -> None:
    """Create a new branch in a GitHub repository.

    Args:
        area: The Area being executed
        params: Action parameters with 'repo_owner', 'repo_name', 'branch_name', 'from_branch' (default: main)
        event: Event data from trigger
    """

    try:
        # Extract parameters
        repo_owner = params.get("repo_owner")
        repo_name = params.get("repo_name")
        branch_name = params.get("branch_name")
        from_branch = params.get("from_branch", "main")

        logger.info(
            "Starting GitHub create_branch action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "branch_name": branch_name,
                "from_branch": from_branch,
                "params": params,
            },
        )

        if not repo_owner or not repo_name:
            raise ValueError("'repo_owner' and 'repo_name' parameters are required for create_branch action")
        if not branch_name:
            raise ValueError("'branch_name' parameter is required for create_branch action")

        # Get GitHub access token
        access_token = _get_github_access_token(area)

        # First, get the SHA of the source branch
        source_ref_endpoint = f"/repos/{repo_owner}/{repo_name}/git/ref/heads/{from_branch}"
        source_ref = _make_github_request("GET", source_ref_endpoint, access_token)
        sha = source_ref["object"]["sha"]

        # Create new branch
        create_ref_endpoint = f"/repos/{repo_owner}/{repo_name}/git/refs"
        ref_data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha,
        }
        result = _make_github_request("POST", create_ref_endpoint, access_token, json_data=ref_data)

        logger.info(
            "GitHub branch created successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "branch_name": branch_name,
                "from_branch": from_branch,
                "sha": sha,
            }
        )
    except Exception as e:
        logger.error(
            "Error creating GitHub branch",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


__all__ = [
    "create_issue_handler",
    "add_comment_handler",
    "close_issue_handler",
    "add_label_handler",
    "create_branch_handler",
]
