"""Google Calendar polling scheduler for trigger-based automation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from app.core.encryption import decrypt_token
from app.core.config import settings
from app.integrations.variable_extractor import extract_calendar_variables
from app.models.area import Area
from app.schemas.execution_log import ExecutionLogCreate
from app.services.execution_logs import create_execution_log
from app.services.service_connections import (
    get_service_connection_by_user_and_service,
    update_service_connection,
)
from app.schemas.service_connection import ServiceConnectionUpdate
from app.services.step_executor import execute_area

logger = logging.getLogger("area")

# In-memory storage for last seen event IDs and processed events
_last_seen_events: Dict[str, set[str]] = {}
_calendar_scheduler_task: asyncio.Task | None = None


def _get_calendar_service(user_id, db: Session):
    """Get authenticated Google Calendar service for a user.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        Calendar service object or None if connection not found
    """
    try:
        connection = get_service_connection_by_user_and_service(db, user_id, "google_calendar")
        if not connection:
            return None

        access_token = decrypt_token(connection.encrypted_access_token)
        refresh_token = None
        if connection.encrypted_refresh_token:
            refresh_token = decrypt_token(connection.encrypted_refresh_token)

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )

        # Refresh if needed and persist new access token
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                update_service_connection(
                    db,
                    str(connection.id),
                    ServiceConnectionUpdate(
                        service_name=connection.service_name,
                        access_token=creds.token,
                        expires_at=creds.expiry,
                    ),
                )
            except RefreshError as refresh_err:
                logger.warning(
                    f"Google Calendar token expired or revoked for user {user_id}. "
                    f"User needs to reconnect their Google Calendar account."
                )
                return None
            except Exception as refresh_err:
                logger.error(f"Failed to refresh Google Calendar token: {refresh_err}")
                return None

        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Failed to get Google Calendar service: {e}", exc_info=True)
        return None


def _fetch_events(service, time_min: str, time_max: str, max_results: int = 50) -> list[dict]:
    """Fetch events from Google Calendar API.

    Args:
        service: Calendar API service
        time_min: RFC3339 timestamp for minimum time
        time_max: RFC3339 timestamp for maximum time
        max_results: Maximum number of events to fetch

    Returns:
        List of event objects
    """
    try:
        results = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return results.get('items', [])
    except RefreshError:
        # Token expired/revoked - already logged in _get_calendar_service
        return []
    except HttpError as e:
        logger.error(f"Google Calendar API error fetching events: {e}", exc_info=True)
        return []


def _extract_event_data(event: dict) -> dict:
    """Extract relevant data from Calendar event.

    Args:
        event: Full Calendar event object

    Returns:
        Dictionary with extracted event data
    """
    start = event.get('start', {})
    end = event.get('end', {})

    # Handle both dateTime (timed events) and date (all-day events)
    start_time = start.get('dateTime') or start.get('date')
    end_time = end.get('dateTime') or end.get('date')

    # Extract attendees
    attendees = event.get('attendees', [])
    attendee_emails = [att.get('email', '') for att in attendees]

    return {
        'id': event.get('id'),
        'summary': event.get('summary', ''),
        'description': event.get('description', ''),
        'location': event.get('location', ''),
        'start_time': start_time,
        'end_time': end_time,
        'timezone': start.get('timeZone', 'UTC'),
        'attendees': attendee_emails,
        'organizer': event.get('organizer', {}).get('email', ''),
        'status': event.get('status', ''),
        'html_link': event.get('htmlLink', ''),
        'created': event.get('created', ''),
        'updated': event.get('updated', ''),
        'is_all_day': 'date' in start,  # All-day events use 'date' instead of 'dateTime'
    }


def _fetch_due_calendar_areas(db: Session) -> list[Area]:
    """Fetch all enabled areas with Google Calendar triggers.

    Args:
        db: Database session

    Returns:
        List of Area objects
    """
    return (
        db.query(Area)
        .filter(
            Area.enabled == True,  # noqa: E712
            Area.trigger_service == "google_calendar",
        )
        .all()
    )


async def calendar_scheduler_task() -> None:
    """Background task that polls Google Calendar for events based on AREA triggers."""
    from app.db.session import SessionLocal

    logger.info("Starting Google Calendar polling scheduler task")

    while True:
        try:
            # Poll at configurable interval (default: 15 seconds)
            await asyncio.sleep(settings.calendar_poll_interval_seconds)

            now = datetime.now(timezone.utc)

            # Fetch all enabled Calendar areas using a scoped session
            with SessionLocal() as db:
                areas = await asyncio.to_thread(_fetch_due_calendar_areas, db)

                logger.info(
                    f"Calendar scheduler tick: found {len(areas)} calendar area(s)",
                    extra={
                        "utc_now": now.isoformat(),
                        "areas_count": len(areas),
                        "area_ids": [str(a.id) for a in areas] if areas else [],
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
                        # Get Calendar service for user
                        service = await asyncio.to_thread(_get_calendar_service, area.user_id, db)
                        if not service:
                            logger.warning(
                                f"Calendar service not available for area {area_id_str}, skipping"
                            )
                            continue

                        # Build query based on trigger action
                        events = await _fetch_events_for_trigger(service, area, now)

                        if not events:
                            continue

                        # On first run for this area, prime the seen set to avoid backlog
                        if len(_last_seen_events[area_id_str]) == 0:
                            _last_seen_events[area_id_str].update(e['id'] for e in events)
                            logger.info(
                                f"Initialized seen set for area {area_id_str} with {len(events)} event(s)"
                            )
                            continue

                        # Filter for new events
                        new_events = [
                            evt for evt in events
                            if evt['id'] not in _last_seen_events[area_id_str]
                        ]

                        if new_events:
                            logger.info(
                                f"Found {len(new_events)} NEW event(s) for area {area_id_str}",
                                extra={
                                    "area_id": area_id_str,
                                    "area_name": area.name,
                                    "user_id": str(area.user_id),
                                    "new_events_count": len(new_events),
                                    "event_ids": [e['id'] for e in new_events],
                                }
                            )

                        # Process each new event
                        for cal_event in new_events:
                            await _process_calendar_trigger(db, area, cal_event, now)
                            # Mark as seen
                            _last_seen_events[area_id_str].add(cal_event['id'])

                except RefreshError as e:
                    # Token expired/revoked - show clean warning
                    logger.warning(
                        f"Calendar area {area_id_str} skipped: token expired or revoked. "
                        f"User needs to reconnect Google Calendar account."
                    )
                except Exception as e:
                    logger.error(
                        "Error processing Calendar area",
                        extra={
                            "area_id": area_id_str,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            logger.info("Calendar scheduler task cancelled, shutting down gracefully")
            break

        except Exception as e:
            logger.error("Calendar scheduler task error", extra={"error": str(e)}, exc_info=True)
            await asyncio.sleep(30)  # Back off on error

    logger.info("Calendar scheduler task stopped")


async def _fetch_events_for_trigger(service, area: Area, now: datetime) -> list[dict]:
    """Fetch events based on trigger type.

    Args:
        service: Calendar API service
        area: Area with trigger configuration
        now: Current timestamp

    Returns:
        List of matching events
    """
    trigger_action = area.trigger_action
    params = area.trigger_params or {}

    if trigger_action == "event_created":
        # Fetch all upcoming events (next 30 days)
        # We track which ones are new via the seen set
        time_min = now.isoformat()
        time_max = (now + timedelta(days=30)).isoformat()
        return await asyncio.to_thread(_fetch_events, service, time_min, time_max, 100)

    elif trigger_action == "event_starting_soon":
        # Fetch events starting within the specified minutes
        minutes_before = int(params.get("minutes_before", 15))
        time_min = now.isoformat()
        time_max = (now + timedelta(minutes=minutes_before + 1)).isoformat()
        return await asyncio.to_thread(_fetch_events, service, time_min, time_max, 20)

    return []


async def _process_calendar_trigger(db: Session, area: Area, cal_event: dict, now: datetime) -> None:
    """Process a Calendar trigger event and execute the area.

    Args:
        db: Database session
        area: Area to execute
        cal_event: Calendar event data
        now: Current timestamp
    """
    # Re-attach the Area instance to the current session
    area = db.merge(area)
    area_id_str = str(area.id)
    execution_log = None

    try:
        # Extract event data
        event_data = _extract_event_data(cal_event)

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
                    "event_id": event_data.get('id'),
                    "summary": event_data.get('summary'),
                }
            }
        )
        execution_log = create_execution_log(db, execution_log_start)

        # Use extract_calendar_variables to get variables from event
        variables = extract_calendar_variables(event_data)

        # Build trigger_data with calendar variables
        trigger_data = {
            **variables,  # Include all extracted calendar.* variables
            "now": now.isoformat(),
            "timestamp": now.timestamp(),
            "area_id": area_id_str,
            "user_id": str(area.user_id),
        }

        # Execute area
        result = execute_area(db, area, trigger_data)

        # Update execution log
        execution_log.status = "Success" if result["status"] == "success" else "Failed"
        execution_log.output = f"Calendar trigger executed: {result['steps_executed']} step(s)"
        execution_log.error_message = result.get("error")
        execution_log.step_details = {
            "execution_log": result.get("execution_log", []),
            "steps_executed": result["steps_executed"],
            "event_id": event_data.get('id'),
        }
        db.commit()

        logger.info(
            "Calendar trigger executed",
            extra={
                "area_id": area_id_str,
                "area_name": area.name,
                "user_id": str(area.user_id),
                "event_id": event_data.get('id'),
                "summary": event_data.get('summary'),
                "start_time": event_data.get('start_time'),
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
            "Error executing Calendar trigger",
            extra={
                "area_id": area_id_str,
                "error": str(e),
            },
            exc_info=True,
        )


def start_calendar_scheduler() -> None:
    """Start the Google Calendar polling scheduler task."""
    global _calendar_scheduler_task

    if _calendar_scheduler_task is not None:
        logger.warning("Calendar scheduler task already running")
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("No event loop running, cannot start Calendar scheduler")
        return

    _calendar_scheduler_task = loop.create_task(calendar_scheduler_task())
    logger.info("Calendar scheduler task started")


def stop_calendar_scheduler() -> None:
    """Stop the Google Calendar polling scheduler task."""
    global _calendar_scheduler_task

    if _calendar_scheduler_task is not None:
        _calendar_scheduler_task.cancel()
        _calendar_scheduler_task = None
        logger.info("Calendar scheduler task stopped")


def is_calendar_scheduler_running() -> bool:
    """Check if the Calendar scheduler task is running.

    Returns:
        True if scheduler is running and not done/cancelled, False otherwise
    """
    global _calendar_scheduler_task
    return _calendar_scheduler_task is not None and not _calendar_scheduler_task.done()


def clear_calendar_seen_state() -> None:
    """Clear the in-memory seen events state (useful for testing)."""
    global _last_seen_events
    _last_seen_events.clear()


__all__ = [
    "calendar_scheduler_task",
    "start_calendar_scheduler",
    "is_calendar_scheduler_running",
    "stop_calendar_scheduler",
    "clear_calendar_seen_state",
]
