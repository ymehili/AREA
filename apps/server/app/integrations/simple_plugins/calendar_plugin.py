"""Google Calendar plugin for AREA - Implements calendar automation actions and reactions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

from app.db.session import SessionLocal
from app.services.service_connections import (
    get_service_connection_by_user_and_service,
    update_service_connection,
)
from app.schemas.service_connection import ServiceConnectionUpdate
from app.core.config import settings
from app.integrations.simple_plugins.exceptions import (
    CalendarAuthError,
    CalendarAPIError,
    CalendarConnectionError,
)

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")


def _get_calendar_service(area: Area, db=None):
    """Get authenticated Google Calendar API service for a user.

    Args:
        area: The Area containing user_id
        db: Database session (optional, will create if not provided)

    Returns:
        Google Calendar API service object

    Raises:
        Exception: If service connection not found or authentication fails
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Get service connection for Google Calendar
        connection = get_service_connection_by_user_and_service(
            db, area.user_id, "google_calendar"
        )
        if not connection:
            raise CalendarConnectionError(
                "Google Calendar service connection not found. Please connect your Google Calendar account."
            )

        # Create credentials from stored tokens
        from app.core.encryption import decrypt_token

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

        # Auto-refresh if expired and persist new token
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
            except Exception as refresh_err:
                logger.error(
                    "Failed to refresh Google Calendar token",
                    extra={
                        "user_id": str(area.user_id),
                        "area_id": str(area.id),
                        "error": str(refresh_err),
                    },
                    exc_info=True,
                )
                raise CalendarAuthError(
                    "Failed to refresh Google Calendar token"
                ) from refresh_err

        # Build Calendar service
        service = build("calendar", "v3", credentials=creds)
        return service
    finally:
        if close_db:
            db.close()


def create_event_handler(area: Area, params: dict, event: dict) -> None:
    """Create a new calendar event.

    Args:
        area: The Area being executed
        params: Action parameters with 'title', 'start_time', 'end_time', 'description', 'location', 'attendees'
        event: Event data from trigger
    """
    try:
        # Extract parameters
        title = params.get("title")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        description = params.get("description", "")
        location = params.get("location", "")
        attendees = params.get("attendees", "")

        logger.info(
            "Starting Calendar create_event action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "params": params,
            },
        )

        if not title:
            raise ValueError("'title' parameter is required for create_event action")
        if not start_time:
            raise ValueError(
                "'start_time' parameter is required for create_event action"
            )
        if not end_time:
            raise ValueError("'end_time' parameter is required for create_event action")

        # Get Calendar service
        service = _get_calendar_service(area)

        # Build event body
        event_body = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {
                "dateTime": start_time,
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time,
                "timeZone": "UTC",
            },
        }

        # Add attendees if provided
        if attendees:
            attendee_list = [{"email": email.strip()} for email in attendees.split(",")]
            event_body["attendees"] = attendee_list

        # Create event
        result = (
            service.events().insert(calendarId="primary", body=event_body).execute()
        )

        logger.info(
            "Calendar event created successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "event_id": result.get("id"),
                "event_link": result.get("htmlLink"),
                "title": title,
            },
        )
    except HttpError as e:
        logger.error(
            "Google Calendar API error creating event",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise CalendarAPIError(f"Failed to create calendar event: {e}") from e
    except Exception as e:
        logger.error(
            "Error creating calendar event",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise


def update_event_handler(area: Area, params: dict, event: dict) -> None:
    """Update an existing calendar event.

    Args:
        area: The Area being executed
        params: Action parameters with 'event_id', optional 'title', 'start_time', 'end_time', 'description', 'location'
        event: Event data from trigger
    """
    try:
        # Get event ID from params or event
        event_id = params.get("event_id")
        if not event_id:
            event_id = event.get("calendar.event_id") or event.get("event_id")

        logger.info(
            "Starting Calendar update_event action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "event_id": event_id,
                "params": params,
            },
        )

        if not event_id:
            raise ValueError(
                "'event_id' is required to update event. Use {{calendar.event_id}} from trigger."
            )

        # Get Calendar service
        service = _get_calendar_service(area)

        # Fetch existing event
        existing_event = (
            service.events().get(calendarId="primary", eventId=event_id).execute()
        )

        # Update fields if provided
        if "title" in params and params["title"]:
            existing_event["summary"] = params["title"]
        if "description" in params:
            existing_event["description"] = params["description"]
        if "location" in params:
            existing_event["location"] = params["location"]
        if "start_time" in params and params["start_time"]:
            existing_event["start"] = {
                "dateTime": params["start_time"],
                "timeZone": "UTC",
            }
        if "end_time" in params and params["end_time"]:
            existing_event["end"] = {
                "dateTime": params["end_time"],
                "timeZone": "UTC",
            }

        # Update event
        result = (
            service.events()
            .update(calendarId="primary", eventId=event_id, body=existing_event)
            .execute()
        )

        logger.info(
            "Calendar event updated successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "event_id": event_id,
                "event_link": result.get("htmlLink"),
            },
        )
    except HttpError as e:
        logger.error(
            "Google Calendar API error updating event",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise CalendarAPIError(f"Failed to update calendar event: {e}") from e
    except Exception as e:
        logger.error(
            "Error updating calendar event",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise


def delete_event_handler(area: Area, params: dict, event: dict) -> None:
    """Delete a calendar event.

    Args:
        area: The Area being executed
        params: Action parameters with 'event_id'
        event: Event data from trigger
    """
    try:
        # Get event ID from params or event
        event_id = params.get("event_id")
        if not event_id:
            event_id = event.get("calendar.event_id") or event.get("event_id")

        logger.info(
            "Starting Calendar delete_event action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "event_id": event_id,
                "params": params,
            },
        )

        if not event_id:
            raise ValueError(
                "'event_id' is required to delete event. Use {{calendar.event_id}} from trigger."
            )

        # Get Calendar service
        service = _get_calendar_service(area)

        # Delete event
        service.events().delete(calendarId="primary", eventId=event_id).execute()

        logger.info(
            "Calendar event deleted successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "event_id": event_id,
            },
        )
    except HttpError as e:
        logger.error(
            "Google Calendar API error deleting event",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise CalendarAPIError(f"Failed to delete calendar event: {e}") from e
    except Exception as e:
        logger.error(
            "Error deleting calendar event",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise


def create_all_day_event_handler(area: Area, params: dict, event: dict) -> None:
    """Create an all-day calendar event.

    Args:
        area: The Area being executed
        params: Action parameters with 'title', 'date', 'description'
        event: Event data from trigger
    """
    try:
        # Extract parameters
        title = params.get("title")
        date = params.get("date")
        description = params.get("description", "")

        logger.info(
            "Starting Calendar create_all_day_event action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "title": title,
                "date": date,
                "params": params,
            },
        )

        if not title:
            raise ValueError(
                "'title' parameter is required for create_all_day_event action"
            )
        if not date:
            raise ValueError(
                "'date' parameter is required for create_all_day_event action"
            )

        # Get Calendar service
        service = _get_calendar_service(area)

        # Build event body for all-day event
        event_body = {
            "summary": title,
            "description": description,
            "start": {
                "date": date,
            },
            "end": {
                "date": date,
            },
        }

        # Create event
        result = (
            service.events().insert(calendarId="primary", body=event_body).execute()
        )

        logger.info(
            "All-day calendar event created successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "event_id": result.get("id"),
                "event_link": result.get("htmlLink"),
                "title": title,
                "date": date,
            },
        )
    except HttpError as e:
        logger.error(
            "Google Calendar API error creating all-day event",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise CalendarAPIError(f"Failed to create all-day calendar event: {e}") from e
    except Exception as e:
        logger.error(
            "Error creating all-day calendar event",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise


def quick_add_event_handler(area: Area, params: dict, event: dict) -> None:
    """Create a calendar event using natural language.

    Args:
        area: The Area being executed
        params: Action parameters with 'text' (e.g., "Meeting tomorrow at 3pm")
        event: Event data from trigger
    """
    try:
        # Extract parameters
        text = params.get("text")

        logger.info(
            "Starting Calendar quick_add_event action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "text": text,
                "params": params,
            },
        )

        if not text:
            raise ValueError("'text' parameter is required for quick_add_event action")

        # Get Calendar service
        service = _get_calendar_service(area)

        # Quick add event using natural language
        result = service.events().quickAdd(calendarId="primary", text=text).execute()

        logger.info(
            "Calendar event created via quick add",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "event_id": result.get("id"),
                "event_link": result.get("htmlLink"),
                "text": text,
                "parsed_summary": result.get("summary"),
            },
        )
    except HttpError as e:
        logger.error(
            "Google Calendar API error using quick add",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise CalendarAPIError(f"Failed to create event via quick add: {e}") from e
    except Exception as e:
        logger.error(
            "Error using quick add",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )
        raise


__all__ = [
    "create_event_handler",
    "update_event_handler",
    "delete_event_handler",
    "create_all_day_event_handler",
    "quick_add_event_handler",
]
