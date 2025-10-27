"""Discord polling scheduler for message trigger-based automation."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
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


# Rate limiter for Discord API calls in scheduler that respects Discord's rate limits
class DiscordRateLimiter:
    def __init__(self):
        """Initialize rate limiter with Discord's rate limit parameters."""
        self.global_limit_reset_time = 0  # Time when global rate limit resets
        self.route_limits = {}  # Store rate limits for each endpoint
        self.lock = asyncio.Lock()  # To prevent race conditions
    
    async def wait_if_needed(self, route: str = "general") -> None:
        """Wait if rate limit would be exceeded for the given route."""
        async with self.lock:
            current_time = time.time()
            
            # Check if global rate limit is active
            if current_time < self.global_limit_reset_time:
                sleep_time = self.global_limit_reset_time - current_time
                logger.warning(f"Discord API global rate limit active in scheduler, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                return
            
            # Check if route-specific rate limit is active
            if route in self.route_limits:
                route_info = self.route_limits[route]
                
                # If we're past the reset time for this route, reset counters
                if current_time >= route_info['reset_time']:
                    route_info['remaining'] = route_info['limit']
                    route_info['reset_time'] = current_time + (route_info.get('reset_after', 1))
                
                # If no requests remaining, wait until reset
                if route_info['remaining'] <= 0:
                    sleep_time = route_info['reset_time'] - current_time
                    if sleep_time > 0:
                        logger.warning(f"Discord API rate limit for route {route} in scheduler, sleeping for {sleep_time:.2f}s")
                        await asyncio.sleep(sleep_time)
    
    async def update_rate_limit_info(self, route: str, response: httpx.Response) -> None:
        """Update rate limit info based on response headers."""
        async with self.lock:
            current_time = time.time()
            
            # Check for global rate limit
            if response.status_code == 429:
                try:
                    data = response.json()
                    retry_after = data.get('retry_after', 1.0)
                    is_global = data.get('global', False)
                    
                    if is_global:
                        self.global_limit_reset_time = current_time + retry_after
                        logger.warning(f"Global rate limit hit in scheduler, reset in {retry_after}s")
                    else:
                        # Update route-specific rate limit
                        self.route_limits[route] = {
                            'limit': data.get('limit', 1),
                            'remaining': 0,
                            'reset_time': current_time + retry_after,
                            'reset_after': retry_after
                        }
                except Exception:
                    # Fallback if response is not JSON
                    self.global_limit_reset_time = current_time + 1.0
            
            # Check for rate limit headers - properly handle mocked responses
            else:
                try:
                    # Check if the header exists in the response
                    if hasattr(response.headers, '__contains__') and 'X-RateLimit-Limit' in response.headers:
                        limit = int(response.headers['X-RateLimit-Limit'])
                        remaining = int(response.headers['X-RateLimit-Remaining'])
                        reset_after = float(response.headers.get('X-RateLimit-Reset-After', 1.0))
                        
                        # Calculate reset time (Discord sends reset_after as seconds from now)
                        reset_time = current_time + reset_after
                        
                        self.route_limits[route] = {
                            'limit': limit,
                            'remaining': remaining,
                            'reset_time': reset_time,
                            'reset_after': reset_after
                        }
                        
                        logger.debug(f"Updated rate limit info for {route} in scheduler: {remaining}/{limit} remaining, resets in {reset_after}s")
                except (ValueError, KeyError):
                    # Headers might be missing or malformed
                    pass
    
    async def decrement_remaining(self, route: str) -> None:
        """Decrement the remaining count for the given route."""
        async with self.lock:
            if route in self.route_limits:
                if self.route_limits[route]['remaining'] > 0:
                    self.route_limits[route]['remaining'] -= 1


# LRU Cache implementation for tracking seen messages and reactions
class LRUCache:
    def __init__(self, max_size: int = 1000):
        """
        Initialize an LRU cache with a maximum size.
        
        Args:
            max_size: Maximum number of items to keep in the cache
        """
        self.max_size = max_size
        self.cache = OrderedDict()
    
    def add(self, key: str) -> None:
        """Add a key to the cache."""
        if key in self.cache:
            # Move existing key to end (mark as most recently used)
            self.cache.move_to_end(key)
        else:
            # Add new key
            self.cache[key] = time.time()
            
            # If cache is too large, remove oldest item
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)  # Remove oldest (first) item
    
    def contains(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        return key in self.cache
    
    def remove_area_cache(self, area_id: str) -> None:
        """Remove cache entries for a specific area ID (when area is deleted/disabled)."""
        keys_to_remove = [key for key in self.cache.keys() if key.startswith(f"{area_id}:")]
        for key in keys_to_remove:
            self.cache.pop(key, None)
    
    def clear_area_entries(self, area_id: str) -> None:
        """Clear all cache entries for a specific area ID."""
        self.remove_area_cache(area_id)
    
    def set_area_entries(self, area_id: str, message_ids: set[str]) -> None:
        """Set cache entries for a specific area ID with given message IDs (for testing)."""
        # Clear existing entries for this area
        self.remove_area_cache(area_id)
        # Add each message ID to the cache
        for msg_id in message_ids:
            cache_key = f"{area_id}:{msg_id}"
            self.add(cache_key)


# Global cache instances with reasonable limits
_last_seen_messages = LRUCache(max_size=10000)  # Max 10k message IDs across all areas
_last_seen_reactions = LRUCache(max_size=5000)  # Max 5k reaction records across all areas
_discord_scheduler_task: asyncio.Task | None = None

# Global rate limiter instance
_discord_scheduler_rate_limiter = DiscordRateLimiter()


def validate_discord_id(value: str | None) -> str:
    """Validate a Discord ID to ensure it's a valid snowflake ID format.
    
    Discord IDs are 64-bit integers typically 17-19 digits long.
    
    Args:
        value: The ID to validate
        
    Returns:
        The validated ID
        
    Raises:
        ValueError: If the ID is invalid
    """
    if value is None:
        raise ValueError("Discord ID cannot be None")
    
    if not isinstance(value, str):
        value = str(value)
    
    if not value.isdigit() or len(value) < 17 or len(value) > 19:
        raise ValueError(f"Invalid Discord ID format: {value}. Must be 17-19 digits.")
    
    return value


async def _fetch_channel_messages(channel_id: str, limit: int = 10) -> list[dict]:
    """Fetch recent messages from a Discord channel.

    Args:
        channel_id: Discord channel ID
        limit: Maximum number of messages to fetch

    Returns:
        List of message objects from Discord API
    """
    from app.core.encryption import get_discord_bot_token
    
    bot_token = get_discord_bot_token()
    if not bot_token:
        logger.error("Discord bot token not configured")
        return []

    try:
        route = f"GET:/channels/{channel_id}/messages"
        await _discord_scheduler_rate_limiter.wait_if_needed(route)
        
        with httpx.Client() as client:
            response = client.get(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers={
                    "Authorization": f"Bot {bot_token}",
                },
                params={"limit": limit},
                timeout=10.0
            )
            
            # Update rate limit info based on response
            await _discord_scheduler_rate_limiter.update_rate_limit_info(route, response)
            
            # Handle rate limit response (429) with exponential backoff
            if response.status_code == 429:
                try:
                    data = response.json()
                    retry_after = data.get('retry_after', 1.0)
                    is_global = data.get('global', False)
                    
                    logger.warning(f"Discord API rate limited in scheduler (global: {is_global}), waiting {retry_after}s")
                    
                    # Sleep for the required time
                    await asyncio.sleep(retry_after)
                    
                    # Retry the request
                    response = client.get(
                        f"https://discord.com/api/v10/channels/{channel_id}/messages",
                        headers={
                            "Authorization": f"Bot {bot_token}",
                        },
                        params={"limit": limit},
                        timeout=10.0
                    )
                    
                    # Update rate limit info for the retry
                    await _discord_scheduler_rate_limiter.update_rate_limit_info(route, response)
                except Exception as e:
                    logger.error(f"Error handling rate limit response: {e}")
                    return []
            
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch Discord messages: {e}", exc_info=True)
        return []


async def _fetch_message_reactions(channel_id: str, message_id: str) -> list[dict]:
    """Fetch a specific message with its reactions from Discord.

    Args:
        channel_id: Discord channel ID
        message_id: Discord message ID

    Returns:
        List of reaction objects from the message
    """
    from app.core.encryption import get_discord_bot_token
    
    bot_token = get_discord_bot_token()
    if not bot_token:
        logger.error("Discord bot token not configured")
        return []

    try:
        route = f"GET:/channels/{channel_id}/messages/{message_id}"
        await _discord_scheduler_rate_limiter.wait_if_needed(route)
        
        with httpx.Client() as client:
            response = client.get(
                f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}",
                headers={
                    "Authorization": f"Bot {bot_token}",
                },
                timeout=10.0
            )
            
            # Update rate limit info based on response
            await _discord_scheduler_rate_limiter.update_rate_limit_info(route, response)
            
            # Handle rate limit response (429) with exponential backoff
            if response.status_code == 429:
                try:
                    data = response.json()
                    retry_after = data.get('retry_after', 1.0)
                    is_global = data.get('global', False)
                    
                    logger.warning(f"Discord API rate limited in scheduler (global: {is_global}), waiting {retry_after}s")
                    
                    # Sleep for the required time
                    await asyncio.sleep(retry_after)
                    
                    # Retry the request
                    response = client.get(
                        f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}",
                        headers={
                            "Authorization": f"Bot {bot_token}",
                        },
                        timeout=10.0
                    )
                    
                    # Update rate limit info for the retry
                    await _discord_scheduler_rate_limiter.update_rate_limit_info(route, response)
                except Exception as e:
                    logger.error(f"Error handling rate limit response: {e}")
                    return []
            
            response.raise_for_status()
            message_data = response.json()
            return message_data.get('reactions', [])
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch Discord message reactions: {e}", exc_info=True)
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
        'author_is_bot': author.get('bot', False),
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


def _extract_reaction_data(reaction: dict, message_id: str, channel_id: str) -> dict:
    """Extract relevant data from Discord reaction.

    Args:
        reaction: Discord reaction object
        message_id: ID of the message that was reacted to
        channel_id: ID of the channel containing the message

    Returns:
        Dictionary with extracted reaction data for variable resolution
    """
    emoji = reaction.get('emoji', {})
    
    return {
        'message_id': message_id,
        'channel_id': channel_id,
        'emoji_name': emoji.get('name', ''),
        'emoji_id': emoji.get('id'),
        'emoji_animated': emoji.get('animated', False),
        'count': reaction.get('count', 0),
        'me': reaction.get('me', False),
    }


def _fetch_due_discord_areas(db: Session, trigger_type: str | None = None) -> list[Area]:
    """Fetch all enabled areas with Discord triggers.

    Args:
        db: Database session
        trigger_type: Optional trigger type filter (e.g., "new_message_in_channel", "reaction_added")

    Returns:
        List of Area objects
    """
    query = db.query(Area).filter(
        Area.enabled == True,  # noqa: E712
        Area.trigger_service == "discord",
    )
    
    if trigger_type:
        query = query.filter(Area.trigger_action == trigger_type)
    
    return query.all()


async def discord_scheduler_task() -> None:
    """Background task that polls Discord channels for new messages and reactions based on AREA triggers."""
    from app.db.session import SessionLocal

    logger.info("Starting Discord polling scheduler task")

    while True:
        try:
            # Poll every 10 seconds (Discord API rate limits apply)
            await asyncio.sleep(10)

            now = datetime.now(timezone.utc)

            # Fetch all enabled Discord areas using a scoped session
            with SessionLocal() as db:
                message_areas = await asyncio.to_thread(_fetch_due_discord_areas, db, "new_message_in_channel")
                reaction_areas = await asyncio.to_thread(_fetch_due_discord_areas, db, "reaction_added")

                logger.info("Discord scheduler tick")

            # Process message trigger areas
            for area in message_areas:
                area_id_str = str(area.id)

                try:
                    # Use scoped session for this area's processing
                    with SessionLocal() as db:
                        # Get channel_id from trigger params
                        params = area.trigger_params or {}
                        channel_id = params.get("channel_id")
                        
                        if not channel_id:
                            logger.warning(
                                f"Missing channel_id for Discord message area {area_id_str}, skipping"
                            )
                            continue

                        # Validate Discord channel ID
                        try:
                            channel_id = validate_discord_id(channel_id)
                        except ValueError as e:
                            logger.error(f"Invalid channel_id for area {area_id_str}: {str(e)}, skipping")
                            continue

                        # Fetch recent messages from the channel
                        messages = await _fetch_channel_messages(channel_id)

                        # Check if this is the first run for this area by checking if any messages from this area exist in the cache
                        first_run = True
                        for msg in messages:
                            cache_key = f"{area_id_str}:{msg['id']}"
                            if _last_seen_messages.contains(cache_key):
                                first_run = False
                                break

                        # On first run for this area, prime the seen cache with fetched IDs to avoid backlog
                        if first_run and messages:
                            for msg in messages:
                                cache_key = f"{area_id_str}:{msg['id']}"
                                _last_seen_messages.add(cache_key)
                            logger.info(
                                f"Initialized seen cache for Discord message area {area_id_str} with {len(messages)} message(s)"
                            )

                        logger.debug(
                            f"Discord fetched {len(messages)} message(s) for area {area_id_str}",
                        )

                        # Filter for new messages (exclude bot messages to prevent infinite loops)
                        new_messages = []
                        for msg in messages:
                            cache_key = f"{area_id_str}:{msg['id']}"
                            # Also check if author exists to prevent errors when author is missing
                            author_data = msg.get('author', {})
                            if not _last_seen_messages.contains(cache_key) and not author_data.get('bot', False):
                                new_messages.append(msg)

                        if new_messages:
                            logger.info(
                                f"Found {len(new_messages)} NEW Discord message(s) for area {area_id_str}",
                            )

                        # Process each new message (oldest first)
                        for message in reversed(new_messages):
                            await _process_discord_trigger(db, area, message, now)
                            # Mark as seen by adding to cache
                            cache_key = f"{area_id_str}:{message['id']}"
                            _last_seen_messages.add(cache_key)

                except Exception as e:
                    logger.error(
                        f"Error processing Discord message area {area_id_str}: {str(e)}",
                        exc_info=True,
                    )

            # Process reaction trigger areas
            for area in reaction_areas:
                area_id_str = str(area.id)

                try:
                    # Use scoped session for this area's processing
                    with SessionLocal() as db:
                        # Get channel_id and message_id from trigger params
                        params = area.trigger_params or {}
                        channel_id = params.get("channel_id")
                        message_id = params.get("message_id")
                        
                        if not channel_id or not message_id:
                            logger.warning(
                                f"Missing channel_id or message_id for Discord reaction area {area_id_str}, skipping"
                            )
                            continue

                        # Validate Discord IDs
                        try:
                            channel_id = validate_discord_id(channel_id)
                            message_id = validate_discord_id(message_id)
                        except ValueError as e:
                            logger.error(f"Invalid Discord IDs for area {area_id_str}: {str(e)}, skipping")
                            continue

                        # Fetch reactions from the specific message
                        reactions = await _fetch_message_reactions(channel_id, message_id)

                        # Check if this is the first run by checking if any reactions from this area/message exist in the cache
                        first_run = True
                        for reaction in reactions:
                            emoji_key = reaction.get('emoji', {}).get('name', '')
                            cache_key = f"{area_id_str}:{message_id}:{emoji_key}"
                            if _last_seen_reactions.contains(cache_key):
                                first_run = False
                                break

                        # On first run, prime the seen cache with fetched reactions to avoid backlog
                        if first_run and reactions:
                            for reaction in reactions:
                                emoji_key = reaction.get('emoji', {}).get('name', '')
                                cache_key = f"{area_id_str}:{message_id}:{emoji_key}"
                                _last_seen_reactions.add(cache_key)
                            logger.info(
                                f"Initialized reaction cache for Discord reaction area {area_id_str} with {len(reactions)} reaction(s)"
                            )
                            continue  # Skip processing on first run

                        logger.debug(
                            f"Discord fetched {len(reactions)} reaction(s) for area {area_id_str}",
                        )

                        # Check for new reactions
                        for reaction in reactions:
                            emoji_key = reaction.get('emoji', {}).get('name', '')
                            cache_key = f"{area_id_str}:{message_id}:{emoji_key}"
                            
                            # Check if this is a new reaction (not seen before)
                            if not _last_seen_reactions.contains(cache_key):
                                logger.info(
                                    f"Found NEW Discord reaction for area {area_id_str}: {emoji_key}",
                                )
                                
                                await _process_discord_reaction_trigger(db, area, reaction, message_id, channel_id, now)
                                # Mark as seen by adding to cache
                                _last_seen_reactions.add(cache_key)

                except Exception as e:
                    logger.error(
                        f"Error processing Discord reaction area {area_id_str}: {str(e)}",
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            logger.info("Discord scheduler task cancelled, shutting down gracefully")
            break

        except Exception as e:
            logger.error(f"Discord scheduler task error: {str(e)}", exc_info=True)
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
            "discord.author.is_bot": message_data.get('author_is_bot'),
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


async def _process_discord_reaction_trigger(
    db: Session, area: Area, reaction: dict, message_id: str, channel_id: str, now: datetime
) -> None:
    """Process a Discord reaction trigger event and execute the area.

    Args:
        db: Database session
        area: Area to execute
        reaction: Discord reaction data
        message_id: ID of the message that was reacted to
        channel_id: ID of the channel containing the message
        now: Current timestamp
    """
    # Re-attach the Area instance to the current session
    area = db.merge(area)
    area_id_str = str(area.id)
    execution_log = None

    try:
        # Extract reaction data
        reaction_data = _extract_reaction_data(reaction, message_id, channel_id)

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
                    "message_id": message_id,
                    "emoji": reaction_data.get('emoji_name'),
                }
            }
        )
        execution_log = create_execution_log(db, execution_log_start)

        # Build trigger_data with discord reaction variables
        trigger_data = {
            # Discord reaction variables
            "discord.reaction.message_id": reaction_data.get('message_id'),
            "discord.reaction.channel_id": reaction_data.get('channel_id'),
            "discord.reaction.emoji_name": reaction_data.get('emoji_name'),
            "discord.reaction.emoji_id": reaction_data.get('emoji_id'),
            "discord.reaction.emoji_animated": reaction_data.get('emoji_animated'),
            "discord.reaction.count": reaction_data.get('count'),
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
        execution_log.output = f"Discord reaction trigger executed: {result['steps_executed']} step(s)"
        execution_log.error_message = result.get("error")
        execution_log.step_details = {
            "execution_log": result.get("execution_log", []),
            "steps_executed": result["steps_executed"],
            "message_id": message_id,
            "emoji": reaction_data.get('emoji_name'),
        }
        db.commit()

        logger.info(
            "Discord reaction trigger executed",
            extra={
                "area_id": area_id_str,
                "area_name": area.name,
                "user_id": str(area.user_id),
                "message_id": message_id,
                "channel_id": channel_id,
                "emoji": reaction_data.get('emoji_name'),
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
            "Error executing Discord reaction trigger",
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
    """Clear the in-memory seen messages and reactions state (useful for testing)."""
    global _last_seen_messages, _last_seen_reactions
    _last_seen_messages = LRUCache(max_size=10000)  # Reset to empty cache
    _last_seen_reactions = LRUCache(max_size=5000)  # Reset to empty cache


def clear_area_from_seen_state(area_id: str) -> None:
    """Remove all cache entries for a specific area ID (when area is deleted/disabled)."""
    global _last_seen_messages, _last_seen_reactions
    _last_seen_messages.remove_area_cache(area_id)
    _last_seen_reactions.remove_area_cache(area_id)


__all__ = [
    "discord_scheduler_task",
    "start_discord_scheduler",
    "is_discord_scheduler_running",
    "stop_discord_scheduler",
    "clear_discord_seen_state",
    "clear_area_from_seen_state",
]
