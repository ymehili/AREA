"""GitHub polling scheduler for trigger-based automation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

import httpx

from app.core.encryption import decrypt_token
from app.core.config import settings
from app.integrations.variable_extractor import extract_github_variables
from app.models.area import Area
from app.schemas.execution_log import ExecutionLogCreate
from app.services.execution_logs import create_execution_log
from app.services.service_connections import get_service_connection_by_user_and_service
from app.services.step_executor import execute_area

logger = logging.getLogger("area")

# In-memory storage for last seen event IDs per AREA
_last_seen_events: Dict[str, set[str]] = {}
_github_scheduler_task: asyncio.Task | None = None

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


def _get_github_access_token(user_id, db: Session) -> str | None:
    """Get GitHub access token for a user.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        GitHub access token or None if connection not found
    """
    try:
        connection = get_service_connection_by_user_and_service(db, user_id, "github")
        if not connection:
            return None

        access_token = decrypt_token(connection.encrypted_access_token)
        return access_token
    except Exception as e:
        logger.error(f"Failed to get GitHub access token: {e}", exc_info=True)
        return None


async def _make_github_request(
    method: str,
    endpoint: str,
    access_token: str,
    params: dict = None,
) -> dict | list | None:
    """Make an authenticated request to GitHub API.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint
        access_token: GitHub access token
        params: Query parameters

    Returns:
        Response JSON or None on error
    """
    url = f"{GITHUB_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "AREA-App/1.0",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPError as e:
            logger.error(f"GitHub API error: {e}", exc_info=True)
            return None


def _fetch_due_github_areas(db: Session) -> list[Area]:
    """Fetch all enabled areas with GitHub triggers.

    Args:
        db: Database session

    Returns:
        List of Area objects
    """
    return (
        db.query(Area)
        .filter(
            Area.enabled == True,  # noqa: E712
            Area.trigger_service == "github",
        )
        .all()
    )


async def _fetch_github_events(
    access_token: str,
    trigger_action: str,
    trigger_params: dict,
) -> list[dict]:
    """Fetch GitHub events based on trigger action.

    Args:
        access_token: GitHub access token
        trigger_action: Trigger action type
        trigger_params: Trigger parameters

    Returns:
        List of event objects
    """
    repo_owner = trigger_params.get("repo_owner")
    repo_name = trigger_params.get("repo_name")

    if not repo_owner or not repo_name:
        logger.warning(f"Missing repo_owner or repo_name for GitHub trigger: {trigger_action}")
        return []

    events = []

    try:
        if trigger_action == "new_issue":
            # Fetch recent issues
            endpoint = f"/repos/{repo_owner}/{repo_name}/issues"
            params = {"state": "open", "sort": "created", "direction": "desc", "per_page": 10}
            issues = await _make_github_request("GET", endpoint, access_token, params=params)
            if issues:
                for issue in issues:
                    # Filter out pull requests (GitHub API returns PRs as issues)
                    if "pull_request" not in issue:
                        events.append({
                            "type": "issues",
                            "action": "opened",
                            "id": f"issue_{issue['id']}",
                            "issue": issue,
                            "repository": {
                                "name": repo_name,
                                "full_name": f"{repo_owner}/{repo_name}",
                            },
                            "sender": issue.get("user", {}),
                        })

        elif trigger_action == "pull_request_opened":
            # Fetch recent pull requests
            endpoint = f"/repos/{repo_owner}/{repo_name}/pulls"
            params = {"state": "open", "sort": "created", "direction": "desc", "per_page": 10}
            prs = await _make_github_request("GET", endpoint, access_token, params=params)
            if prs:
                for pr in prs:
                    events.append({
                        "type": "pull_request",
                        "action": "opened",
                        "id": f"pr_{pr['id']}",
                        "pull_request": pr,
                        "repository": {
                            "name": repo_name,
                            "full_name": f"{repo_owner}/{repo_name}",
                        },
                        "sender": pr.get("user", {}),
                    })

        elif trigger_action == "push_to_repository":
            # Fetch recent commits via events API
            endpoint = f"/repos/{repo_owner}/{repo_name}/events"
            params = {"per_page": 10}
            repo_events = await _make_github_request("GET", endpoint, access_token, params=params)
            if repo_events:
                for event in repo_events:
                    if event.get("type") == "PushEvent":
                        events.append({
                            "type": "push",
                            "action": "pushed",
                            "id": event["id"],
                            "commits": event.get("payload", {}).get("commits", []),
                            "ref": event.get("payload", {}).get("ref", ""),
                            "repository": {
                                "name": repo_name,
                                "full_name": f"{repo_owner}/{repo_name}",
                            },
                            "sender": event.get("actor", {}),
                        })

        elif trigger_action == "release_published":
            # Fetch recent releases
            endpoint = f"/repos/{repo_owner}/{repo_name}/releases"
            params = {"per_page": 10}
            releases = await _make_github_request("GET", endpoint, access_token, params=params)
            if releases:
                for release in releases:
                    events.append({
                        "type": "release",
                        "action": "published",
                        "id": f"release_{release['id']}",
                        "release": release,
                        "repository": {
                            "name": repo_name,
                            "full_name": f"{repo_owner}/{repo_name}",
                        },
                        "sender": release.get("author", {}),
                    })

        elif trigger_action == "repository_starred":
            # Fetch stargazers (recent stars)
            endpoint = f"/repos/{repo_owner}/{repo_name}/stargazers"
            params = {"per_page": 10}
            headers_override = {"Accept": "application/vnd.github.v3.star+json"}
            # Note: This requires custom headers, simplified for now
            # In production, track star count changes instead
            pass

    except Exception as e:
        logger.error(f"Error fetching GitHub events for {trigger_action}: {e}", exc_info=True)

    return events


async def github_scheduler_task() -> None:
    """Background task that polls GitHub for events based on AREA triggers."""
    from app.db.session import SessionLocal

    logger.info("Starting GitHub polling scheduler task")

    while True:
        try:
            # Poll at 30-second intervals (configurable)
            await asyncio.sleep(30)

            now = datetime.now(timezone.utc)

            # Fetch all enabled GitHub areas using a scoped session
            with SessionLocal() as db:
                areas = await asyncio.to_thread(_fetch_due_github_areas, db)

                logger.info(
                    "GitHub scheduler tick",
                    extra={
                        "utc_now": now.isoformat(),
                        "areas_count": len(areas),
                    },
                )

            # Process each area with its own scoped session
            for area in areas:
                area_id_str = str(area.id)

                # Initialize last seen events set for this area
                if area_id_str not in _last_seen_events:
                    _last_seen_events[area_id_str] = set()

                try:
                    # Use scoped session for this area's processing
                    with SessionLocal() as db:
                        # Get GitHub access token for user
                        access_token = await asyncio.to_thread(_get_github_access_token, area.user_id, db)
                        if not access_token:
                            logger.warning(
                                f"GitHub access token not available for area {area_id_str}, skipping"
                            )
                            continue

                        # Fetch events based on trigger action
                        events = await _fetch_github_events(
                            access_token,
                            area.trigger_action,
                            area.trigger_params or {},
                        )

                        # On first run for this area, prime the seen set to avoid backlog
                        if len(_last_seen_events[area_id_str]) == 0 and events:
                            _last_seen_events[area_id_str].update(e["id"] for e in events)
                            logger.info(
                                f"Initialized seen set for area {area_id_str} with {len(events)} event(s)"
                            )
                            continue

                        logger.info(
                            f"GitHub fetched {len(events)} event(s) for area {area_id_str}",
                            extra={
                                "area_id": area_id_str,
                                "area_name": area.name,
                                "user_id": str(area.user_id),
                                "events_fetched": len(events),
                                "trigger_action": area.trigger_action,
                            }
                        )

                        # Filter for new events
                        new_events = [
                            event for event in events
                            if event["id"] not in _last_seen_events[area_id_str]
                        ]

                        if new_events:
                            logger.info(
                                f"Found {len(new_events)} NEW event(s) for area {area_id_str}",
                                extra={
                                    "area_id": area_id_str,
                                    "area_name": area.name,
                                    "user_id": str(area.user_id),
                                    "new_events_count": len(new_events),
                                    "event_ids": [e["id"] for e in new_events],
                                }
                            )

                        # Process each new event
                        for event in new_events:
                            await _process_github_trigger(db, area, event, now)
                            # Mark as seen
                            _last_seen_events[area_id_str].add(event["id"])

                except Exception as e:
                    logger.error(
                        "Error processing GitHub area",
                        extra={
                            "area_id": area_id_str,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            logger.info("GitHub scheduler task cancelled, shutting down gracefully")
            break

        except Exception as e:
            logger.error("GitHub scheduler task error", extra={"error": str(e)}, exc_info=True)
            await asyncio.sleep(30)  # Back off on error

    logger.info("GitHub scheduler task stopped")


async def _process_github_trigger(db: Session, area: Area, event: dict, now: datetime) -> None:
    """Process a GitHub trigger event and execute the area.

    Args:
        db: Database session
        area: Area to execute
        event: GitHub event data
        now: Current timestamp
    """
    # Re-attach the Area instance to the current session
    area = db.merge(area)
    area_id_str = str(area.id)
    execution_log = None

    try:
        # Create execution log entry
        execution_log_start = ExecutionLogCreate(
            area_id=area.id,
            status="Started",
            output=None,
            error_message=None,
            step_details={
                "event": {
                    "now": now.isoformat(),
                    "area_id": area_id_str,
                    "user_id": str(area.user_id),
                    "event_type": event.get("type"),
                    "event_action": event.get("action"),
                }
            }
        )
        execution_log = create_execution_log(db, execution_log_start)

        # Use extract_github_variables to get variables from event
        variables = extract_github_variables(event)

        # Build trigger_data with github variables
        trigger_data = {
            **variables,  # Include all extracted github.* variables
            "now": now.isoformat(),
            "timestamp": now.timestamp(),
            "area_id": area_id_str,
            "user_id": str(area.user_id),
        }

        # Execute area
        result = execute_area(db, area, trigger_data)

        # Update execution log
        execution_log.status = "Success" if result["status"] == "success" else "Failed"
        execution_log.output = f"GitHub trigger executed: {result['steps_executed']} step(s)"
        execution_log.error_message = result.get("error")
        execution_log.step_details = {
            "execution_log": result.get("execution_log", []),
            "steps_executed": result["steps_executed"],
            "event_type": event.get("type"),
            "event_id": event.get("id"),
        }
        db.commit()

        logger.info(
            "GitHub trigger executed",
            extra={
                "area_id": area_id_str,
                "area_name": area.name,
                "user_id": str(area.user_id),
                "event_type": event.get("type"),
                "event_action": event.get("action"),
                "status": result["status"],
                "steps_executed": result.get("steps_executed", 0),
            },
        )

    except Exception as e:
        # Update execution log with failure
        if execution_log:
            execution_log.status = "Failed"
            execution_log.error_message = str(e)
            db.commit()

        logger.error(
            "Error executing GitHub trigger",
            extra={
                "area_id": area_id_str,
                "error": str(e),
            },
            exc_info=True,
        )


def start_github_scheduler() -> None:
    """Start the GitHub polling scheduler task."""
    global _github_scheduler_task

    if _github_scheduler_task is not None:
        logger.warning("GitHub scheduler task already running")
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("No event loop running, cannot start GitHub scheduler")
        return

    _github_scheduler_task = loop.create_task(github_scheduler_task())
    logger.info("GitHub scheduler task started")


def stop_github_scheduler() -> None:
    """Stop the GitHub polling scheduler task."""
    global _github_scheduler_task

    if _github_scheduler_task is not None:
        _github_scheduler_task.cancel()
        _github_scheduler_task = None
        logger.info("GitHub scheduler task stopped")


def is_github_scheduler_running() -> bool:
    """Check if the GitHub scheduler task is running.

    Returns:
        True if scheduler is running and not done/cancelled, False otherwise
    """
    global _github_scheduler_task
    return _github_scheduler_task is not None and not _github_scheduler_task.done()


def clear_github_seen_state() -> None:
    """Clear the in-memory seen events state (useful for testing)."""
    global _last_seen_events
    _last_seen_events.clear()


__all__ = [
    "github_scheduler_task",
    "start_github_scheduler",
    "is_github_scheduler_running",
    "stop_github_scheduler",
    "clear_github_seen_state",
]
