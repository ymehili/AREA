"""Gmail polling scheduler for trigger-based automation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
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
from app.integrations.variable_extractor import extract_gmail_variables
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
_gmail_scheduler_task: asyncio.Task | None = None


def _get_gmail_service(user_id, db: Session):
    """Get authenticated Gmail service for a user.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        Gmail service object or None if connection not found
    """
    try:
        connection = get_service_connection_by_user_and_service(db, user_id, "gmail")
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
                # Persist updated access token and expiry
                update_service_connection(
                    db,
                    str(connection.id),
                    ServiceConnectionUpdate(
                        service_name=connection.service_name,
                        access_token=creds.token,
                        # Keep same refresh token (Google rarely rotates it)
                        expires_at=creds.expiry,
                    ),
                )
            except RefreshError:
                logger.warning(
                    f"Gmail token expired or revoked for user {user_id}. "
                    f"User needs to reconnect their Gmail account."
                )
                return None
            except Exception as refresh_err:
                logger.error(f"Failed to refresh Gmail token: {refresh_err}")
                return None

        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        logger.error(f"Failed to get Gmail service: {e}", exc_info=True)
        return None


def _fetch_messages(service, query: str, max_results: int = 10) -> list[dict]:
    """Fetch messages from Gmail API.

    Args:
        service: Gmail API service
        query: Gmail search query
        max_results: Maximum number of messages to fetch

    Returns:
        List of message objects with full details
    """
    try:
        # List messages matching query
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        # Fetch full details for each message
        full_messages = []
        for msg in messages:
            try:
                full_msg = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                full_messages.append(full_msg)
            except HttpError as e:
                logger.warning(f"Failed to fetch message {msg['id']}: {e}")
                continue

        return full_messages
    except RefreshError:
        # Token expired/revoked - already logged in _get_gmail_service
        return []
    except HttpError as e:
        logger.error(f"Gmail API error fetching messages: {e}", exc_info=True)
        return []


def _extract_message_data(message: dict) -> dict:
    """Extract relevant data from Gmail message.

    Args:
        message: Full Gmail message object

    Returns:
        Dictionary with extracted message data
    """
    headers = message.get('payload', {}).get('headers', [])

    # Extract headers
    sender = ""
    subject = ""
    date = ""
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        if name == 'from':
            sender = value
        elif name == 'subject':
            subject = value
        elif name == 'date':
            date = value

    return {
        'id': message.get('id'),
        'threadId': message.get('threadId'),
        'snippet': message.get('snippet', ''),
        'labelIds': message.get('labelIds', []),
        'payload': {
            'headers': [
                {'name': 'From', 'value': sender},
                {'name': 'Subject', 'value': subject},
                {'name': 'Date', 'value': date},
            ]
        },
        # Add extracted fields for easy access
        'sender': sender,
        'subject': subject,
        'date': date,
    }


def _fetch_due_gmail_areas(db: Session) -> list[Area]:
    """Fetch all enabled areas with Gmail triggers.

    Args:
        db: Database session

    Returns:
        List of Area objects
    """
    return (
        db.query(Area)
        .filter(
            Area.enabled == True,  # noqa: E712
            Area.trigger_service == "gmail",
        )
        .all()
    )


async def gmail_scheduler_task() -> None:
    """Background task that polls Gmail for new messages based on AREA triggers."""
    from app.db.session import SessionLocal

    logger.info("Starting Gmail polling scheduler task")

    while True:
        try:
            # Poll at configurable interval (default: 60 seconds)
            await asyncio.sleep(settings.gmail_poll_interval_seconds)

            now = datetime.now(timezone.utc)

            # Fetch all enabled Gmail areas using a scoped session
            with SessionLocal() as db:
                areas = await asyncio.to_thread(_fetch_due_gmail_areas, db)

                logger.info(
                    "Gmail scheduler tick",
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

                try:
                    # Use scoped session for this area's processing
                    with SessionLocal() as db:
                        # Get Gmail service for user
                        service = await asyncio.to_thread(_get_gmail_service, area.user_id, db)
                        if not service:
                            logger.warning(
                                f"Gmail service not available for area {area_id_str}, skipping"
                            )
                            continue

                        # Build query based on trigger action
                        query = _build_gmail_query(area)
                        if not query:
                            logger.warning(
                                f"Unknown Gmail trigger action: {area.trigger_action} for area {area_id_str}"
                            )
                            continue

                        # Fetch messages
                        messages = await asyncio.to_thread(_fetch_messages, service, query)

                        # On first run for this area, prime the seen set with fetched IDs to avoid backlog
                        if len(_last_seen_messages[area_id_str]) == 0 and messages:
                            _last_seen_messages[area_id_str].update(m['id'] for m in messages)
                            logger.info(
                                f"Initialized seen set for area {area_id_str} with {len(messages)} message(s)"
                            )

                        logger.info(
                            f"Gmail fetched {len(messages)} message(s) for area {area_id_str}, "
                            f"already seen: {len(_last_seen_messages[area_id_str])}",
                            extra={
                                "area_id": area_id_str,
                                "area_name": area.name,
                                "user_id": str(area.user_id),
                                "messages_fetched": len(messages),
                                "messages_already_seen": len(_last_seen_messages[area_id_str]),
                                "query": query,
                            }
                        )

                        # Filter for new messages
                        new_messages = [
                            msg for msg in messages
                            if msg['id'] not in _last_seen_messages[area_id_str]
                        ]

                        if new_messages:
                            logger.info(
                                f"Found {len(new_messages)} NEW message(s) for area {area_id_str}",
                                extra={
                                    "area_id": area_id_str,
                                    "area_name": area.name,
                                    "user_id": str(area.user_id),
                                    "new_messages_count": len(new_messages),
                                    "message_ids": [msg['id'] for msg in new_messages],
                                }
                            )

                        # Process each new message
                        for message in new_messages:
                            await _process_gmail_trigger(db, area, message, now)
                            # Mark as seen
                            _last_seen_messages[area_id_str].add(message['id'])

                except RefreshError:
                    # Token expired/revoked - show clean warning
                    logger.warning(
                        f"Gmail area {area_id_str} skipped: token expired or revoked. "
                        f"User needs to reconnect Gmail account."
                    )
                except Exception as e:
                    logger.error(
                        "Error processing Gmail area",
                        extra={
                            "area_id": area_id_str,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            logger.info("Gmail scheduler task cancelled, shutting down gracefully")
            break

        except Exception as e:
            logger.error("Gmail scheduler task error", extra={"error": str(e)}, exc_info=True)
            await asyncio.sleep(30)  # Back off on error

    logger.info("Gmail scheduler task stopped")


def _build_gmail_query(area: Area) -> str | None:
    """Build Gmail search query based on trigger action and params.

    Args:
        area: Area with Gmail trigger

    Returns:
        Gmail search query string or None
    """
    trigger_action = area.trigger_action
    params = area.trigger_params or {}

    if trigger_action == "new_email":
        # All new emails in inbox
        return "in:inbox"

    elif trigger_action == "new_email_from_sender":
        # New emails from specific sender
        sender = params.get("sender_email")
        if sender:
            return f"from:{sender} in:inbox"
        return "in:inbox"

    elif trigger_action == "new_unread_email":
        # New unread emails
        return "is:unread in:inbox"

    elif trigger_action == "email_starred":
        # Starred emails
        return "is:starred"

    return None


async def _process_gmail_trigger(db: Session, area: Area, message: dict, now: datetime) -> None:
    """Process a Gmail trigger event and execute the area.

    Args:
        db: Database session
        area: Area to execute
        message: Gmail message data
        now: Current timestamp
    """
    # Re-attach the Area instance to the current session so lazy-loaded
    # relationships (like `steps`) can be accessed during execution.
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
                    "message_id": message_data.get('id'),
                    "subject": message_data.get('subject'),
                }
            }
        )
        execution_log = create_execution_log(db, execution_log_start)

        # Use extract_gmail_variables to get variables from message
        variables = extract_gmail_variables(message_data)

        # Build trigger_data with gmail variables
        trigger_data = {
            **variables,  # Include all extracted gmail.* variables
            "now": now.isoformat(),
            "timestamp": now.timestamp(),
            "area_id": area_id_str,
            "user_id": str(area.user_id),
        }

        # Execute area
        result = execute_area(db, area, trigger_data)

        # Update execution log
        execution_log.status = "Success" if result["status"] == "success" else "Failed"
        execution_log.output = f"Gmail trigger executed: {result['steps_executed']} step(s)"
        execution_log.error_message = result.get("error")
        execution_log.step_details = {
            "execution_log": result.get("execution_log", []),
            "steps_executed": result["steps_executed"],
            "message_id": message_data.get('id'),
        }
        db.commit()

        logger.info(
            "Gmail trigger executed",
            extra={
                "area_id": area_id_str,
                "area_name": area.name,
                "user_id": str(area.user_id),
                "message_id": message_data.get('id'),
                "thread_id": message_data.get('threadId'),
                "subject": message_data.get('subject'),
                "sender": message_data.get('sender'),
                "snippet": message_data.get('snippet'),
                "date": message_data.get('date'),
                "status": result["status"],
                "steps_executed": result.get("steps_executed", 0),
                "execution_log": result.get("execution_log", []),
            },
        )

    except Exception as e:
        # Update execution log with failure
        if execution_log:
            execution_log.status = "Failed"
            execution_log.error_message = str(e)
            db.commit()

        logger.error(
            "Error executing Gmail trigger",
            extra={
                "area_id": area_id_str,
                "error": str(e),
            },
            exc_info=True,
        )


def start_gmail_scheduler() -> None:
    """Start the Gmail polling scheduler task."""
    global _gmail_scheduler_task

    if _gmail_scheduler_task is not None:
        logger.warning("Gmail scheduler task already running")
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("No event loop running, cannot start Gmail scheduler")
        return

    _gmail_scheduler_task = loop.create_task(gmail_scheduler_task())
    logger.info("Gmail scheduler task started")


def stop_gmail_scheduler() -> None:
    """Stop the Gmail polling scheduler task."""
    global _gmail_scheduler_task

    if _gmail_scheduler_task is not None:
        _gmail_scheduler_task.cancel()
        _gmail_scheduler_task = None
        logger.info("Gmail scheduler task stopped")


def is_gmail_scheduler_running() -> bool:
    """Check if the Gmail scheduler task is running.

    Returns:
        True if scheduler is running and not done/cancelled, False otherwise
    """
    global _gmail_scheduler_task
    return _gmail_scheduler_task is not None and not _gmail_scheduler_task.done()


def clear_gmail_seen_state() -> None:
    """Clear the in-memory seen messages state (useful for testing)."""
    global _last_seen_messages
    _last_seen_messages.clear()


__all__ = [
    "gmail_scheduler_task",
    "start_gmail_scheduler",
    "is_gmail_scheduler_running",
    "stop_gmail_scheduler",
    "clear_gmail_seen_state",
]
