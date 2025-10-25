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

# Rate limiter for Discord API calls
class DiscordRateLimiter:
    def __init__(self, max_requests: int = 50, time_window: int = 1):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed per time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_make_request(self) -> bool:
        """Check if a request can be made based on rate limits."""
        current_time = time.time()
        
        # Remove requests that are outside the time window
        self.requests = [req_time for req_time in self.requests if current_time - req_time < self.time_window]
        
        # Check if we're under the limit
        return len(self.requests) < self.max_requests
    
    def record_request(self):
        """Record that a request was made."""
        self.requests.append(time.time())
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        if not self.can_make_request():
            sleep_time = self.time_window  # Wait for the time window to reset
            logger.warning(f"Discord API rate limit approaching, sleeping for {sleep_time}s")
            await asyncio.sleep(sleep_time)
        
        # Record the request that will be made
        self.record_request()


# Global rate limiter instance
_discord_rate_limiter = DiscordRateLimiter()


def _make_discord_api_request(method: str, url: str, headers: dict, **kwargs) -> httpx.Response:
    """Make a rate-limited Discord API request with retry logic."""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            # Make the request
            with httpx.Client() as client:
                response = client.request(method, url, headers=headers, **kwargs)
                
                # Check for rate limit response (429)
                if response.status_code == 429:
                    retry_after = response.json().get("retry_after", retry_delay)
                    logger.warning(f"Discord API rate limited, waiting {retry_after}s before retry")
                    time.sleep(retry_after)
                    continue  # Retry the request
                
                # Success or other error - return the response
                return response
        except httpx.HTTPError as e:
            if attempt == max_retries - 1:  # Last attempt
                raise e
            logger.warning(f"Discord API request failed (attempt {attempt + 1}), retrying in {retry_delay}s: {e}")
            time.sleep(retry_delay)
    
    # If all retries failed, return the last response (should not reach here if an exception was raised)
    raise httpx.HTTPError("Max retries exceeded for Discord API request")


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
    
    if not channel_id or not message_template:
        error_msg = f"Discord send_message missing required params: channel_id={channel_id}, message={bool(message_template)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Validate Discord IDs
    try:
        channel_id = validate_discord_id(channel_id)
    except ValueError as e:
        logger.error(f"Invalid channel_id: {str(e)}")
        raise
    
    bot_token = get_discord_bot_token()
    if not bot_token:
        error_msg = "Discord bot token not configured. Set DISCORD_BOT_TOKEN or ENCRYPTED_DISCORD_BOT_TOKEN in .env file."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
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
    
    # Wait if needed due to rate limiting, then send message to the channel using bot token
    await _discord_rate_limiter.wait_if_needed()
    response = _make_discord_api_request(
        "POST",
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        headers={
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10.0
    )
    
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
    
    if not guild_id or not name_template:
        error_msg = f"Discord create_channel missing required params: guild_id={guild_id}, name={bool(name_template)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Validate Discord IDs
    try:
        guild_id = validate_discord_id(guild_id)
    except ValueError as e:
        logger.error(f"Invalid guild_id: {str(e)}")
        raise
    
    bot_token = get_discord_bot_token()
    if not bot_token:
        error_msg = "Discord bot token not configured. Set DISCORD_BOT_TOKEN or ENCRYPTED_DISCORD_BOT_TOKEN in .env file."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Resolve variables in channel name
    channel_name = resolve_variables(name_template, event)
    
    # Wait if needed due to rate limiting, then create the channel
    await _discord_rate_limiter.wait_if_needed()
    response = _make_discord_api_request(
        "POST",
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
