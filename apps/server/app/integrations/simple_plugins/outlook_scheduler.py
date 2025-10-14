"""Outlook polling scheduler for trigger-based automation via Microsoft Graph API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

import httpx

from app.core.encryption import decrypt_token
from app.core.config import settings
from app.integrations.variable_extractor import extract_outlook_variables
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

# In-memory storage for last seen message IDs per AREA
_last_seen_messages: Dict[str, set[str]] = {}
_outlook_scheduler_task: asyncio.Task | None = None


async def _get_outlook_client(user_id, db: Session) -> httpx.AsyncClient | None:
    """Get authenticated httpx client for Microsoft Graph API.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        Authenticated httpx.AsyncClient or None if connection not found
    """
    try:
        connection = get_service_connection_by_user_and_service(db, user_id, "outlook")
        if not connection:
            return None

        # Decrypt tokens
        access_token = decrypt_token(connection.encrypted_access_token)
        refresh_token = None
        if connection.encrypted_refresh_token:
            refresh_token = decrypt_token(connection.encrypted_refresh_token)

        # Check if token is expired
        now = datetime.now(timezone.utc)
        token_expired = False
        if connection.expires_at:
            # Add 5 minute buffer
            token_expired = connection.expires_at <= now + timedelta(minutes=5)

        # Refresh token if expired
        if token_expired and refresh_token:
            try:
                async with httpx.AsyncClient() as temp_client:
                    response = await temp_client.post(
                        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        data={
                            "client_id": settings.microsoft_client_id,
                            "client_secret": settings.microsoft_client_secret,
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token",
                        },
                    )
                    response.raise_for_status()
                    token_data = response.json()

                    # Update tokens
                    access_token = token_data["access_token"]
                    new_refresh_token = token_data.get("refresh_token", refresh_token)
                    expires_in = token_data.get("expires_in", 3600)
                    new_expires_at = now + timedelta(seconds=expires_in)

                    # Persist updated tokens
                    update_service_connection(
                        db,
                        str(connection.id),
                        ServiceConnectionUpdate(
                            service_name=connection.service_name,
                            access_token=access_token,
                            refresh_token=new_refresh_token,
                            expires_at=new_expires_at,
                        ),
                    )
            except Exception as refresh_err:
                logger.error(f"Failed to refresh Outlook token: {refresh_err}")
                return None

        # Create authenticated client
        client = httpx.AsyncClient(
            base_url="https://graph.microsoft.com/v1.0",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        return client
    except Exception as e:
        logger.error(f"Failed to get Outlook client: {e}", exc_info=True)
        return None


async def _fetch_messages(client: httpx.AsyncClient, filter_query: str, max_results: int = 10) -> list[dict]:
    """Fetch messages from Microsoft Graph API.

    Args:
        client: Authenticated httpx client
        filter_query: OData filter query for messages
        max_results: Maximum number of messages to fetch

    Returns:
        List of message objects
    """
    try:
        # Build query parameters
        params = {
            "$top": max_results,
            "$orderby": "receivedDateTime DESC",
        }
        
        if filter_query:
            params["$filter"] = filter_query

        # Fetch messages from Microsoft Graph
        response = await client.get("/me/messages", params=params)
        response.raise_for_status()
        data = response.json()

        return data.get("value", [])
    except httpx.HTTPError as e:
        logger.error(f"Outlook API error fetching messages: {e}", exc_info=True)
        return []


def _extract_message_data(message: dict) -> dict:
    """Extract relevant data from Outlook message.

    Args:
        message: Outlook message object from Microsoft Graph API

    Returns:
        Dictionary with extracted message data
    """
    # Extract sender email
    sender_email = ""
    sender_name = ""
    if message.get("from"):
        sender_email = message["from"].get("emailAddress", {}).get("address", "")
        sender_name = message["from"].get("emailAddress", {}).get("name", "")

    # Extract subject and body preview
    subject = message.get("subject", "")
    body_preview = message.get("bodyPreview", "")
    
    # Extract dates
    received_datetime = message.get("receivedDateTime", "")
    sent_datetime = message.get("sentDateTime", "")

    return {
        "id": message.get("id"),
        "conversationId": message.get("conversationId"),
        "subject": subject,
        "bodyPreview": body_preview,
        "sender_email": sender_email,
        "sender_name": sender_name,
        "received_datetime": received_datetime,
        "sent_datetime": sent_datetime,
        "isRead": message.get("isRead", False),
        "importance": message.get("importance", "normal"),
        "hasAttachments": message.get("hasAttachments", False),
        "webLink": message.get("webLink", ""),
    }


def _fetch_due_outlook_areas(db: Session) -> list[Area]:
    """Fetch all enabled areas with Outlook triggers.

    Args:
        db: Database session

    Returns:
        List of Area objects
    """
    return (
        db.query(Area)
        .filter(
            Area.enabled == True,  # noqa: E712
            Area.trigger_service == "outlook",
        )
        .all()
    )


async def outlook_scheduler_task() -> None:
    """Background task that polls Outlook for new messages based on AREA triggers."""
    from app.db.session import SessionLocal

    logger.info("Starting Outlook polling scheduler task")

    while True:
        try:
            # Poll at configurable interval (default: 60 seconds)
            await asyncio.sleep(settings.outlook_poll_interval_seconds)

            now = datetime.now(timezone.utc)

            # Fetch all enabled Outlook areas using a scoped session
            with SessionLocal() as db:
                areas = await asyncio.to_thread(_fetch_due_outlook_areas, db)

                logger.info(
                    "Outlook scheduler tick",
                    extra={
                        "utc_now": now.isoformat(),
                        "areas_count": len(areas),
                    },
                )

            # Process each area with its own scoped session
            for area in areas:
                area_id_str = str(area.id)

                # Initialize last seen messages set for this area
                if area_id_str not in _last_seen_messages:
                    _last_seen_messages[area_id_str] = set()

                client = None
                try:
                    # Use scoped session for this area's processing
                    with SessionLocal() as db:
                        # Get Outlook client for user
                        client = await _get_outlook_client(area.user_id, db)
                        if not client:
                            logger.warning(
                                f"Outlook client not available for area {area_id_str}, skipping"
                            )
                            continue

                        # Build filter query based on trigger action
                        filter_query = _build_outlook_filter(area)

                        # Fetch messages
                        messages = await _fetch_messages(client, filter_query)

                        # On first run for this area, prime the seen set to avoid backlog
                        if len(_last_seen_messages[area_id_str]) == 0 and messages:
                            _last_seen_messages[area_id_str].update(m["id"] for m in messages)
                            logger.info(
                                f"Initialized seen set for area {area_id_str} with {len(messages)} message(s)"
                            )

                        logger.info(
                            f"Outlook fetched {len(messages)} message(s) for area {area_id_str}, "
                            f"already seen: {len(_last_seen_messages[area_id_str])}",
                            extra={
                                "area_id": area_id_str,
                                "area_name": area.name,
                                "user_id": str(area.user_id),
                                "messages_fetched": len(messages),
                                "messages_already_seen": len(_last_seen_messages[area_id_str]),
                                "filter_query": filter_query,
                            },
                        )

                        # Filter for new messages
                        new_messages = [
                            msg for msg in messages if msg["id"] not in _last_seen_messages[area_id_str]
                        ]

                        if new_messages:
                            logger.info(
                                f"Found {len(new_messages)} NEW message(s) for area {area_id_str}",
                                extra={
                                    "area_id": area_id_str,
                                    "area_name": area.name,
                                    "user_id": str(area.user_id),
                                    "new_messages_count": len(new_messages),
                                    "message_ids": [msg["id"] for msg in new_messages],
                                },
                            )

                        # Process each new message
                        for message in new_messages:
                            await _process_outlook_trigger(db, area, message, now)
                            # Mark as seen
                            _last_seen_messages[area_id_str].add(message["id"])

                except Exception as e:
                    logger.error(
                        "Error processing Outlook area",
                        extra={
                            "area_id": area_id_str,
                            "error": str(e),
                        },
                        exc_info=True,
                    )
                finally:
                    if client:
                        await client.aclose()

        except asyncio.CancelledError:
            logger.info("Outlook scheduler task cancelled, shutting down gracefully")
            break

        except Exception as e:
            logger.error("Outlook scheduler task error", extra={"error": str(e)}, exc_info=True)
            await asyncio.sleep(30)  # Back off on error

    logger.info("Outlook scheduler task stopped")


def _build_outlook_filter(area: Area) -> str:
    """Build Microsoft Graph OData filter query based on trigger action and params.

    Args:
        area: Area with Outlook trigger

    Returns:
        OData filter query string
    """
    trigger_action = area.trigger_action
    params = area.trigger_params or {}

    if trigger_action == "new_email":
        # All new emails in inbox folder
        return "receivedDateTime ge 1900-01-01"

    elif trigger_action == "new_email_from_sender":
        # New emails from specific sender
        sender = params.get("sender_email")
        if sender:
            return f"from/emailAddress/address eq '{sender}'"
        return "receivedDateTime ge 1900-01-01"

    elif trigger_action == "new_unread_email":
        # New unread emails
        return "isRead eq false"

    elif trigger_action == "email_important":
        # Important emails
        return "importance eq 'high'"

    # Default: fetch recent messages
    return "receivedDateTime ge 1900-01-01"


async def _process_outlook_trigger(db: Session, area: Area, message: dict, now: datetime) -> None:
    """Process an Outlook trigger event and execute the area.

    Args:
        db: Database session
        area: Area to execute
        message: Outlook message data
        now: Current timestamp
    """
    # Re-attach the Area instance to the current session
    area = db.merge(area)
    area_id_str = str(area.id)
    execution_log = None

    try:
        # Extract message data
        message_data = _extract_message_data(message)

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
                    "message_id": message_data.get("id"),
                    "subject": message_data.get("subject"),
                }
            },
        )
        execution_log = create_execution_log(db, execution_log_start)

        # Use extract_outlook_variables to get variables from message
        variables = extract_outlook_variables(message_data)

        # Build trigger_data with outlook variables
        trigger_data = {
            **variables,  # Include all extracted outlook.* variables
            "now": now.isoformat(),
            "timestamp": now.timestamp(),
            "area_id": area_id_str,
            "user_id": str(area.user_id),
        }

        # Execute area
        result = execute_area(db, area, trigger_data)

        # Update execution log
        execution_log.status = "Success" if result["status"] == "success" else "Failed"
        execution_log.output = f"Outlook trigger executed: {result['steps_executed']} step(s)"
        execution_log.error_message = result.get("error")
        execution_log.step_details = {
            "execution_log": result.get("execution_log", []),
            "steps_executed": result["steps_executed"],
            "message_id": message_data.get("id"),
        }
        db.commit()

        logger.info(
            "Outlook trigger executed",
            extra={
                "area_id": area_id_str,
                "area_name": area.name,
                "user_id": str(area.user_id),
                "message_id": message_data.get("id"),
                "subject": message_data.get("subject"),
                "sender_email": message_data.get("sender_email"),
                "bodyPreview": message_data.get("bodyPreview"),
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
            "Error executing Outlook trigger",
            extra={
                "area_id": area_id_str,
                "error": str(e),
            },
            exc_info=True,
        )


def start_outlook_scheduler() -> None:
    """Start the Outlook polling scheduler task."""
    global _outlook_scheduler_task

    if _outlook_scheduler_task is not None:
        logger.warning("Outlook scheduler task already running")
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("No event loop running, cannot start Outlook scheduler")
        return

    _outlook_scheduler_task = loop.create_task(outlook_scheduler_task())
    logger.info("Outlook scheduler task started")


def stop_outlook_scheduler() -> None:
    """Stop the Outlook polling scheduler task."""
    global _outlook_scheduler_task

    if _outlook_scheduler_task is not None:
        _outlook_scheduler_task.cancel()
        _outlook_scheduler_task = None
        logger.info("Outlook scheduler task stopped")


def is_outlook_scheduler_running() -> bool:
    """Check if the Outlook scheduler task is running.

    Returns:
        True if scheduler is running and not done/cancelled, False otherwise
    """
    global _outlook_scheduler_task
    return _outlook_scheduler_task is not None and not _outlook_scheduler_task.done()


def clear_outlook_seen_state() -> None:
    """Clear the in-memory seen messages state (useful for testing)."""
    global _last_seen_messages
    _last_seen_messages.clear()


__all__ = [
    "outlook_scheduler_task",
    "start_outlook_scheduler",
    "is_outlook_scheduler_running",
    "stop_outlook_scheduler",
    "clear_outlook_seen_state",
]
