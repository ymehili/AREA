"""Discord polling scheduler for message trigger-based automation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

import httpx

from app.core.config import settings
from app.models.area import Area
from app.schemas.execution_log import ExecutionLogCreate
from app.services.execution_logs import create_execution_log
from app.services.step_executor import execute_area

logger = logging.getLogger("area")

# In-memory storage for last seen message IDs per AREA
_last_seen_messages: Dict[str, set[str]] = {}
_discord_scheduler_task: asyncio.Task | None = None


def _fetch_channel_messages(channel_id: str, limit: int = 10) -> list[dict]:
    """Fetch recent messages from a Discord channel.

    Args:
        channel_id: Discord channel ID
        limit: Maximum number of messages to fetch

    Returns:
        List of message objects from Discord API
    """
    if not settings.discord_bot_token:
        logger.error("Discord bot token not configured")
        return []

    try:
        with httpx.Client() as client:
            response = client.get(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers={
                    "Authorization": f"Bot {settings.discord_bot_token}",
                },
                params={"limit": limit},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch Discord messages: {e}", exc_info=True)
        return []


def _extract_message_data(message: dict) -> dict:
    """Extract relevant data from Discord message.

    Args:
        message: Discord message object

    Returns:
        Dictionary with extracted message data for variable resolution
    """
    author = message.get('author', {})
    
    return {
        'id': message.get('id'),
        'channel_id': message.get('channel_id'),
        'content': message.get('content', ''),
        'timestamp': message.get('timestamp', ''),
        'author_id': author.get('id', ''),
        'author_username': author.get('username', ''),
        'author_discriminator': author.get('discriminator', ''),
        'author_global_name': author.get('global_name', ''),
        'mentions': [user.get('id') for user in message.get('mentions', [])],
        'attachments': [
            {
                'id': att.get('id'),
                'filename': att.get('filename'),
                'url': att.get('url'),
                'content_type': att.get('content_type'),
            }
            for att in message.get('attachments', [])
        ],
        'embeds': message.get('embeds', []),
    }


def _fetch_due_discord_areas(db: Session) -> list[Area]:
    """Fetch all enabled areas with Discord triggers.

    Args:
        db: Database session

    Returns:
        List of Area objects
    """
    return (
        db.query(Area)
        .filter(
            Area.enabled == True,  # noqa: E712
            Area.trigger_service == "discord",
        )
        .all()
    )


async def discord_scheduler_task() -> None:
    """Background task that polls Discord channels for new messages based on AREA triggers."""
    from app.db.session import SessionLocal

    logger.info("Starting Discord polling scheduler task")

    while True:
        try:
            # Poll every 10 seconds (Discord API rate limits apply)
            await asyncio.sleep(10)

            now = datetime.now(timezone.utc)

            # Fetch all enabled Discord areas using a scoped session
            with SessionLocal() as db:
                areas = await asyncio.to_thread(_fetch_due_discord_areas, db)

                logger.info(
                    "Discord scheduler tick",
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
                        # Get channel_id from trigger params
                        params = area.trigger_params or {}
                        channel_id = params.get("channel_id")
                        
                        if not channel_id:
                            logger.warning(
                                f"No channel_id configured for Discord area {area_id_str}, skipping"
                            )
                            continue

                        # Fetch recent messages from the channel
                        messages = await asyncio.to_thread(_fetch_channel_messages, channel_id)

                        # On first run for this area, prime the seen set with fetched IDs to avoid backlog
                        if len(_last_seen_messages[area_id_str]) == 0 and messages:
                            _last_seen_messages[area_id_str].update(m['id'] for m in messages)
                            logger.info(
                                f"Initialized seen set for Discord area {area_id_str} with {len(messages)} message(s)"
                            )

                        logger.debug(
                            f"Discord fetched {len(messages)} message(s) for area {area_id_str}, "
                            f"already seen: {len(_last_seen_messages[area_id_str])}",
                            extra={
                                "area_id": area_id_str,
                                "area_name": area.name,
                                "user_id": str(area.user_id),
                                "messages_fetched": len(messages),
                                "messages_already_seen": len(_last_seen_messages[area_id_str]),
                                "channel_id": channel_id,
                            }
                        )

                        # Filter for new messages
                        new_messages = [
                            msg for msg in messages
                            if msg['id'] not in _last_seen_messages[area_id_str]
                        ]

                        if new_messages:
                            logger.info(
                                f"Found {len(new_messages)} NEW Discord message(s) for area {area_id_str}",
                                extra={
                                    "area_id": area_id_str,
                                    "area_name": area.name,
                                    "user_id": str(area.user_id),
                                    "new_messages_count": len(new_messages),
                                    "message_ids": [msg['id'] for msg in new_messages],
                                }
                            )

                        # Process each new message (oldest first)
                        for message in reversed(new_messages):
                            await _process_discord_trigger(db, area, message, now)
                            # Mark as seen
                            _last_seen_messages[area_id_str].add(message['id'])

                except Exception as e:
                    logger.error(
                        "Error processing Discord area",
                        extra={
                            "area_id": area_id_str,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            logger.info("Discord scheduler task cancelled, shutting down gracefully")
            break

        except Exception as e:
            logger.error("Discord scheduler task error", extra={"error": str(e)}, exc_info=True)
            await asyncio.sleep(30)  # Back off on error

    logger.info("Discord scheduler task stopped")


async def _process_discord_trigger(db: Session, area: Area, message: dict, now: datetime) -> None:
    """Process a Discord message trigger event and execute the area.

    Args:
        db: Database session
        area: Area to execute
        message: Discord message data
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
                    "content_preview": message_data.get('content', '')[:50],
                }
            }
        )
        execution_log = create_execution_log(db, execution_log_start)

        # Build trigger_data with discord variables
        trigger_data = {
            # Discord message variables
            "discord.message.id": message_data.get('id'),
            "discord.message.content": message_data.get('content'),
            "discord.message.timestamp": message_data.get('timestamp'),
            "discord.message.channel_id": message_data.get('channel_id'),
            "discord.author.id": message_data.get('author_id'),
            "discord.author.username": message_data.get('author_username'),
            "discord.author.discriminator": message_data.get('author_discriminator'),
            "discord.author.global_name": message_data.get('author_global_name'),
            "discord.attachments": message_data.get('attachments'),
            "discord.embeds": message_data.get('embeds'),
            # General context
            "now": now.isoformat(),
            "timestamp": now.timestamp(),
            "area_id": area_id_str,
            "user_id": str(area.user_id),
        }

        # Execute area
        result = execute_area(db, area, trigger_data)

        # Update execution log
        execution_log.status = "Success" if result["status"] == "success" else "Failed"
        execution_log.output = f"Discord trigger executed: {result['steps_executed']} step(s)"
        execution_log.error_message = result.get("error")
        execution_log.step_details = {
            "execution_log": result.get("execution_log", []),
            "steps_executed": result["steps_executed"],
            "message_id": message_data.get('id'),
        }
        db.commit()

        logger.info(
            "Discord trigger executed",
            extra={
                "area_id": area_id_str,
                "area_name": area.name,
                "user_id": str(area.user_id),
                "message_id": message_data.get('id'),
                "channel_id": message_data.get('channel_id'),
                "author": message_data.get('author_username'),
                "content_preview": message_data.get('content', '')[:50],
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
            "Error executing Discord trigger",
            extra={
                "area_id": area_id_str,
                "error": str(e),
            },
            exc_info=True,
        )


def start_discord_scheduler() -> None:
    """Start the Discord polling scheduler task."""
    global _discord_scheduler_task

    if _discord_scheduler_task is not None:
        logger.warning("Discord scheduler task already running")
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("No event loop running, cannot start Discord scheduler")
        return

    _discord_scheduler_task = loop.create_task(discord_scheduler_task())
    logger.info("Discord scheduler task started")


def stop_discord_scheduler() -> None:
    """Stop the Discord polling scheduler task."""
    global _discord_scheduler_task

    if _discord_scheduler_task is not None:
        _discord_scheduler_task.cancel()
        _discord_scheduler_task = None
        logger.info("Discord scheduler task stopped")


def is_discord_scheduler_running() -> bool:
    """Check if the Discord scheduler task is running.

    Returns:
        True if scheduler is running and not done/cancelled, False otherwise
    """
    global _discord_scheduler_task
    return _discord_scheduler_task is not None and not _discord_scheduler_task.done()


def clear_discord_seen_state() -> None:
    """Clear the in-memory seen messages state (useful for testing)."""
    global _last_seen_messages
    _last_seen_messages.clear()


__all__ = [
    "discord_scheduler_task",
    "start_discord_scheduler",
    "is_discord_scheduler_running",
    "stop_discord_scheduler",
    "clear_discord_seen_state",
]
