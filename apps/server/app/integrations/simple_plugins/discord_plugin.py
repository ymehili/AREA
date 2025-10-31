"""Discord plugin for sending messages to channels via Discord Bot."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")

# Rate limiter for Discord API calls that respects Discord's rate limits
class DiscordRateLimiter:
    def __init__(self):
        """Initialize rate limiter with Discord's rate limit parameters."""
        self.global_limit_reset_time = 0  # Time when global rate limit resets
        self.route_limits = {}  # Store rate limits for each endpoint
        self.lock = asyncio.Lock()  # To prevent race conditions
    
    async def wait_if_needed(self, route: str) -> None:
        """Wait if rate limit would be exceeded for the given route."""
        async with self.lock:
            current_time = time.time()
            
            # Check if global rate limit is active
            if current_time < self.global_limit_reset_time:
                sleep_time = self.global_limit_reset_time - current_time
                logger.warning(f"Discord API global rate limit active, sleeping for {sleep_time:.2f}s")
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
                        logger.warning(f"Discord API rate limit for route {route}, sleeping for {sleep_time:.2f}s")
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
                        logger.warning(f"Global rate limit hit, reset in {retry_after}s")
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
                        
                        logger.debug(f"Updated rate limit info for {route}: {remaining}/{limit} remaining, resets in {reset_after}s")
                except (ValueError, KeyError):
                    # Headers might be missing or malformed
                    pass
    
    async def decrement_remaining(self, route: str) -> None:
        """Decrement the remaining count for the given route."""
        async with self.lock:
            if route in self.route_limits:
                if self.route_limits[route]['remaining'] > 0:
                    self.route_limits[route]['remaining'] -= 1


# Global rate limiter instance
_discord_rate_limiter = DiscordRateLimiter()


async def validate_discord_id(value: str | None) -> str:
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


async def send_message_handler(area: Area, params: dict, event: dict) -> None:
    """Send a message to a Discord channel using bot token from config.
    
    Args:
        area: The Area being executed
        params: Reaction params containing:
            - channel_id: Discord channel ID where to send the message
            - message: Message content (supports variable templates)
            - attachment_url: Optional URL of an image/video to attach
        event: Event data with trigger context
        
    Raises:
        ValueError: If required parameters are missing or bot token is not configured
        httpx.HTTPError: If the Discord API request fails
    """
    from app.core.config import settings
    from app.core.encryption import get_discord_bot_token
    from app.services.variable_resolver import resolve_variables
    
    channel_id = params.get("channel_id")
    message_template = params.get("message", "")
    attachment_url = params.get("attachment_url", "")
    
    # Check bot token first before processing other parameters
    bot_token = get_discord_bot_token()
    if not bot_token:
        error_msg = "Discord bot token not configured. Set DISCORD_BOT_TOKEN or ENCRYPTED_DISCORD_BOT_TOKEN in .env file."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not channel_id or not message_template:
        error_msg = f"Discord send_message missing required params: channel_id={channel_id}, message={bool(message_template)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Validate Discord IDs
    try:
        channel_id = await validate_discord_id(channel_id)
    except ValueError as e:
        logger.error(f"Invalid channel_id: {str(e)}")
        raise
    
    # Resolve variables in message and attachment URL
    message = resolve_variables(message_template, event)
    if attachment_url:
        attachment_url = resolve_variables(attachment_url, event)
    
    # Prepare the payload
    payload = {"content": message}
    
    # If attachment URL is provided, add it as an embed
    if attachment_url:
        # Discord can display images/videos directly from URLs using embeds
        payload["embeds"] = [{
            "image": {"url": attachment_url} if any(attachment_url.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']) else None,
            "video": {"url": attachment_url} if any(attachment_url.lower().endswith(ext) for ext in ['.mp4', '.webm', '.mov']) else None,
        }]
        # Remove None values
        if payload["embeds"][0].get("image") is None and payload["embeds"][0].get("video") is None:
            # If not image or video, just include URL in message
            payload["content"] = f"{message}\n{attachment_url}"
            del payload["embeds"]
        else:
            # Clean up None fields
            payload["embeds"][0] = {k: v for k, v in payload["embeds"][0].items() if v is not None}
    
    route = f"POST:/channels/{channel_id}/messages"
    await _discord_rate_limiter.wait_if_needed(route)
    
    with httpx.Client() as client:
        response = client.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10.0
        )
    
    # Update rate limit info based on response
    await _discord_rate_limiter.update_rate_limit_info(route, response)
    
    # Handle rate limit response (429) with exponential backoff
    if response.status_code == 429:
        try:
            data = response.json()
            retry_after = data.get('retry_after', 1.0)
            is_global = data.get('global', False)
            
            logger.warning(f"Discord API rate limited (global: {is_global}), waiting {retry_after}s")
            
            # Sleep for the required time
            await asyncio.sleep(retry_after)
            
            # Retry the request
            with httpx.Client() as client:
                response = client.post(
                    f"https://discord.com/api/v10/channels/{channel_id}/messages",
                    headers={
                        "Authorization": f"Bot {bot_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0
                )
                
                # Update rate limit info for the retry
                await _discord_rate_limiter.update_rate_limit_info(route, response)
        except Exception as e:
            logger.error(f"Error handling rate limit response: {e}")
            error_detail = f"Failed to send Discord message: {str(e)}"
            logger.error(error_detail)
            raise
    
    try:
        response.raise_for_status()
        logger.info(f"Discord message sent to channel {channel_id}: {message[:50]}...")
    except httpx.HTTPStatusError as e:
        error_detail = f"Failed to send Discord message: {str(e)}"
        if e.response is not None:
            error_detail += f" - Response: {e.response.text}"
        logger.error(error_detail)
        raise


async def create_channel_handler(area: Area, params: dict, event: dict) -> None:
    """Create a new channel in a Discord server.
    
    Args:
        area: The Area being executed
        params: Reaction params containing:
            - guild_id: Discord server (guild) ID where to create the channel
            - name: Channel name (supports variable templates)
            - type: Channel type (0=text, 2=voice, default=0)
        event: Event data with trigger context
        
    Raises:
        ValueError: If required parameters are missing or bot token is not configured
        httpx.HTTPError: If the Discord API request fails
    """
    from app.core.config import settings
    from app.core.encryption import get_discord_bot_token
    from app.services.variable_resolver import resolve_variables
    
    guild_id = params.get("guild_id")
    name_template = params.get("name", "")
    channel_type = params.get("type", 0)  # 0 = text channel, 2 = voice channel
    
    # Check bot token first before processing other parameters
    bot_token = get_discord_bot_token()
    if not bot_token:
        error_msg = "Discord bot token not configured. Set DISCORD_BOT_TOKEN or ENCRYPTED_DISCORD_BOT_TOKEN in .env file."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not guild_id or not name_template:
        error_msg = f"Discord create_channel missing required params: guild_id={guild_id}, name={bool(name_template)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Validate Discord IDs
    try:
        guild_id = await validate_discord_id(guild_id)
    except ValueError as e:
        logger.error(f"Invalid guild_id: {str(e)}")
        raise
    
    # Resolve variables in channel name
    channel_name = resolve_variables(name_template, event)
    
    route = f"POST:/guilds/{guild_id}/channels"
    await _discord_rate_limiter.wait_if_needed(route)
    
    with httpx.Client() as client:
        response = client.post(
            f"https://discord.com/api/v10/guilds/{guild_id}/channels",
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
            json={
                "name": channel_name,
                "type": channel_type,
            },
            timeout=10.0
        )
    
    # Update rate limit info based on response
    await _discord_rate_limiter.update_rate_limit_info(route, response)
    
    # Handle rate limit response (429) with exponential backoff
    if response.status_code == 429:
        try:
            data = response.json()
            retry_after = data.get('retry_after', 1.0)
            is_global = data.get('global', False)
            
            logger.warning(f"Discord API rate limited (global: {is_global}), waiting {retry_after}s")
            
            # Sleep for the required time
            await asyncio.sleep(retry_after)
            
            # Retry the request
            with httpx.Client() as client:
                response = client.post(
                    f"https://discord.com/api/v10/guilds/{guild_id}/channels",
                    headers={
                        "Authorization": f"Bot {bot_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "name": channel_name,
                        "type": channel_type,
                    },
                    timeout=10.0
                )
                
                # Update rate limit info for the retry
                await _discord_rate_limiter.update_rate_limit_info(route, response)
        except Exception as e:
            logger.error(f"Error handling rate limit response: {e}")
            error_detail = f"Failed to create Discord channel: {str(e)}"
            logger.error(error_detail)
            raise
    
    try:
        response.raise_for_status()
        channel_data = response.json()
        logger.info(f"Discord channel created: {channel_name} (ID: {channel_data.get('id')}) in guild {guild_id}")
    except httpx.HTTPStatusError as e:
        error_detail = f"Failed to create Discord channel: {str(e)}"
        if e.response is not None:
            error_detail += f" - Response: {e.response.text}"
        logger.error(error_detail)
        raise


__all__ = [
    "send_message_handler",
    "create_channel_handler",
    "validate_discord_id",
]
