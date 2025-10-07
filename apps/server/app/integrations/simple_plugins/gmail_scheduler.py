"""Background scheduler for Gmail-based Area triggers."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.core.encryption import decrypt_token
from app.db.session import SessionLocal
from app.integrations.oauth.factory import OAuth2ProviderFactory
from app.integrations.simple_plugins.registry import get_plugins_registry
from app.models.area import Area
from app.models.service_connection import ServiceConnection
from app.schemas.execution_log import ExecutionLogCreate
from app.services.execution_logs import create_execution_log
from app.services.step_executor import execute_area

logger = logging.getLogger("area")

# In-memory storage for last checked times per area
_last_check_by_area_id: Dict[str, datetime] = {}
_gmail_scheduler_task: asyncio.Task | None = None


def _fetch_gmail_enabled_areas(db: Session) -> list[Area]:
    """Fetch all enabled areas with Gmail-based triggers (sync function for thread pool).

    Args:
        db: Database session

    Returns:
        List of Area objects with Gmail triggers
    """
    return (
        db.query(Area)
        .filter(
            Area.enabled == True,  # noqa: E712
            Area.trigger_service == "gmail",
            Area.trigger_action.in_(["new_email", "new_unread_email", "email_starred"]),  # Supported Gmail triggers
        )
        .all()
    )


def _fetch_user_gmail_connection(db: Session, user_id: str) -> ServiceConnection | None:
    """Fetch the Gmail service connection for a user.

    Args:
        db: Database session
        user_id: User ID to find the Gmail connection for

    Returns:
        ServiceConnection object or None if not found
    """
    return (
        db.query(ServiceConnection)
        .filter(
            ServiceConnection.user_id == user_id,
            ServiceConnection.service_name == "gmail",
        )
        .first()
    )


async def is_gmail_area_due(area: Area, now: datetime, last_check: datetime | None, default_interval: int = 30) -> bool:
    """Check if a Gmail area is due to run based on configured interval.

    Args:
        area: The Area to check
        now: Current datetime
        last_check: Last check datetime or None
        default_interval: Default interval in seconds if not specified

    Returns:
        True if the area should run now
    """
    if last_check is None:
        return True

    # Get interval from trigger_params or use default
    # Default to checking every 30 seconds for Gmail triggers to avoid rate limits
    interval_seconds = area.trigger_params.get("interval_seconds", default_interval) if area.trigger_params else default_interval

    # Check if enough time has passed
    elapsed = (now - last_check).total_seconds()
    return elapsed >= interval_seconds


async def _check_and_execute_gmail_area(area: Area, db: Session) -> bool:
    """Check if a Gmail area's trigger condition is met and execute if so.
    
    Args:
        area: The Area to check and potentially execute
        db: Database session
        
    Returns:
        True if area was executed, False otherwise
    """
    # Get user's Gmail connection
    gmail_connection = _fetch_user_gmail_connection(db, str(area.user_id))
    if not gmail_connection:
        logger.warning(f"No Gmail connection found for user {area.user_id}, Area {area.id}")
        return False
    
    # Get OAuth provider
    provider = OAuth2ProviderFactory.create_provider("gmail")
    
    # Decrypt access token
    access_token = decrypt_token(gmail_connection.encrypted_access_token)
    
    # Determine which trigger function to use based on the area's trigger action
    trigger_action = area.trigger_action
    trigger_result = None
    
    try:
        if trigger_action == "new_email":
            # Check for new emails from specific sender
            sender_filter = area.trigger_params.get("sender", "") if area.trigger_params else ""
            subject_contains = area.trigger_params.get("subject_contains", "") if area.trigger_params else ""
            
            query_parts = []
            if sender_filter:
                query_parts.append(f"from:{sender_filter}")
            if subject_contains:
                query_parts.append(f"subject:({subject_contains})")
            
            query = " ".join(query_parts) or "is:unread"  # Default to unread emails if no specific criteria
            
            # Get messages from Gmail
            response = await provider.list_gmail_messages(access_token, query=query)
            messages = response.get("messages", [])
            
            # We'll consider the area triggered if at least one message matches
            if messages:
                # Get the most recent message for event data
                message_id = messages[0]["id"]
                full_message = await provider.get_gmail_message(access_token, message_id)
                
                trigger_result = {
                    "id": full_message["id"],
                    "threadId": full_message["threadId"],
                    "snippet": full_message["snippet"],
                    "payload": full_message.get("payload", {}),
                    "sizeEstimate": full_message.get("sizeEstimate", 0),
                    "historyId": full_message.get("historyId", ""),
                    "internalDate": full_message.get("internalDate", ""),
                }
                
        elif trigger_action == "new_unread_email":
            # Check for new unread emails
            response = await provider.list_gmail_messages(access_token, query="is:unread")
            messages = response.get("messages", [])
            
            if messages:
                # Get the most recent message for event data
                message_id = messages[0]["id"]
                full_message = await provider.get_gmail_message(access_token, message_id)
                
                trigger_result = {
                    "id": full_message["id"],
                    "threadId": full_message["threadId"],
                    "snippet": full_message["snippet"],
                    "payload": full_message.get("payload", {}),
                    "sizeEstimate": full_message.get("sizeEstimate", 0),
                    "historyId": full_message.get("historyId", ""),
                    "internalDate": full_message.get("internalDate", ""),
                }
                
        elif trigger_action == "email_starred":
            # Check for starred emails
            response = await provider.list_gmail_messages(access_token, query="label:STARRED")
            messages = response.get("messages", [])
            
            if messages:
                # Get the most recent message for event data
                message_id = messages[0]["id"]
                full_message = await provider.get_gmail_message(access_token, message_id)
                
                trigger_result = {
                    "id": full_message["id"],
                    "threadId": full_message["threadId"],
                    "snippet": full_message["snippet"],
                    "payload": full_message.get("payload", {}),
                    "sizeEstimate": full_message.get("sizeEstimate", 0),
                    "historyId": full_message.get("historyId", ""),
                    "internalDate": full_message.get("internalDate", ""),
                }
        
        # If trigger condition is met, execute the area
        if trigger_result is not None:
            # Extract variables from the trigger result
            from app.integrations.variable_extractor import extract_gmail_variables
            variables = extract_gmail_variables(trigger_result)
            
            # Create execution log entry for start of execution
            execution_log_start = ExecutionLogCreate(
                area_id=area.id,
                status="Started",
                output=None,
                error_message=None,
                step_details={
                    "event": {
                        "now": datetime.now(timezone.utc).isoformat(),
                        "area_id": str(area.id),
                        "user_id": str(area.user_id),
                        "tick": True,
                        **variables,  # Include Gmail variables in the event
                    }
                }
            )
            execution_log = create_execution_log(db, execution_log_start)

            # Execute area using step executor (supports conditional branching)
            try:
                # Assemble trigger event data with datetime context and Gmail variables
                trigger_data = {
                    "now": datetime.now(timezone.utc).isoformat(),
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                    "year": datetime.now(timezone.utc).year,
                    "month": datetime.now(timezone.utc).month,
                    "day": datetime.now(timezone.utc).day,
                    "hour": datetime.now(timezone.utc).hour,
                    "minute": datetime.now(timezone.utc).minute,
                    "second": datetime.now(timezone.utc).second,
                    "weekday": datetime.now(timezone.utc).weekday(),
                    "area_id": str(area.id),
                    "user_id": str(area.user_id),
                    "tick": True,
                    **variables,  # Include Gmail variables
                    **trigger_result  # Include the full trigger result
                }

                result = execute_area(db, area, trigger_data)

                # Update execution log based on result
                execution_log.status = "Success" if result["status"] == "success" else "Failed"
                execution_log.output = f"Executed {result['steps_executed']} step(s)"
                execution_log.error_message = result.get("error")
                execution_log.step_details = {
                    "execution_log": result.get("execution_log", []),
                    "steps_executed": result["steps_executed"],
                }
                db.commit()

                # Log execution
                logger.info(
                    "Gmail area executed",
                    extra={
                        "area_id": str(area.id),
                        "area_name": area.name,
                        "trigger_action": trigger_action,
                        "status": result["status"],
                        "steps_executed": result["steps_executed"],
                    },
                )
                
                return True  # Area was executed
            except Exception as execution_error:
                # Update execution log with failure status
                execution_log.status = "Failed"
                execution_log.error_message = str(execution_error)
                db.commit()

                logger.error(
                    "Error executing Gmail area",
                    extra={
                        "area_id": str(area.id),
                        "trigger_action": trigger_action,
                        "error": str(execution_error),
                    },
                    exc_info=True,
                )
    
    except Exception as e:
        logger.error(
            f"Error checking Gmail trigger for Area {area.id}: {str(e)}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "trigger_action": trigger_action,
                "error": str(e),
            },
            exc_info=True,
        )
    
    return False  # Area was not executed


async def gmail_scheduler_task() -> None:
    """Background task that checks and executes Gmail-based areas."""
    logger.info("Starting Gmail scheduler task")
    registry = get_plugins_registry()

    while True:
        try:
            await asyncio.sleep(1)  # Check every second

            now = datetime.now(timezone.utc)
            db = SessionLocal()

            try:
                # Load all enabled areas with Gmail triggers (non-blocking)
                areas = await asyncio.to_thread(_fetch_gmail_enabled_areas, db)

                logger.info(
                    "Gmail scheduler tick",
                    extra={
                        "utc_now": now.isoformat(),
                        "areas_count": len(areas),
                    },
                )

                for area in areas:
                    area_id_str = str(area.id)
                    last_check = _last_check_by_area_id.get(area_id_str)

                    # Check if area is due to run
                    if await is_gmail_area_due(area, now, last_check):
                        try:
                            # Check the trigger condition and execute the area if met
                            executed = await _check_and_execute_gmail_area(area, db)
                            
                            if executed:
                                # Update last check time to now if area was executed
                                _last_check_by_area_id[area_id_str] = now
                            else:
                                # Update last check time anyway so we don't check again too soon
                                _last_check_by_area_id[area_id_str] = now

                        except Exception as e:
                            logger.error(
                                "Error in Gmail scheduler processing",
                                extra={
                                    "area_id": area_id_str,
                                    "error": str(e),
                                },
                                exc_info=True,
                            )

            finally:
                db.close()

        except asyncio.CancelledError:
            # Handle cancellation explicitly - let it propagate
            logger.info("Gmail scheduler task cancelled, shutting down gracefully")
            break  # Exit the while loop

        except Exception as e:  # pragma: no cover
            logger.error("Gmail scheduler task error", extra={"error": str(e)}, exc_info=True)
            await asyncio.sleep(5)  # Back off on error

    logger.info("Gmail scheduler task stopped")


def start_gmail_scheduler() -> None:
    """Start the background Gmail scheduler task."""
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
    """Stop the background Gmail scheduler task."""
    global _gmail_scheduler_task

    if _gmail_scheduler_task is not None:
        _gmail_scheduler_task.cancel()
        _gmail_scheduler_task = None
        logger.info("Gmail scheduler task stopped")


def clear_gmail_last_check_state() -> None:
    """Clear the in-memory last check state (useful for testing)."""
    global _last_check_by_area_id
    _last_check_by_area_id.clear()


__all__ = [
    "gmail_scheduler_task",
    "start_gmail_scheduler", 
    "stop_gmail_scheduler",
    "is_gmail_area_due",
    "clear_gmail_last_check_state",
]