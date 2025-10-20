"""Discord plugin for sending messages to channels via Discord Bot."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")


def send_message_handler(area: Area, params: dict, event: dict) -> None:
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
    from app.services.variable_resolver import resolve_variables
    
    channel_id = params.get("channel_id")
    message_template = params.get("message", "")
    attachment_url = params.get("attachment_url", "")
    
    if not channel_id or not message_template:
        error_msg = f"Discord send_message missing required params: channel_id={channel_id}, message={bool(message_template)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not settings.discord_bot_token:
        error_msg = "Discord bot token not configured. Set DISCORD_BOT_TOKEN in .env file."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Resolve variables in message and attachment URL
    message = resolve_variables(message_template, event)
    if attachment_url:
        attachment_url = resolve_variables(attachment_url, event)
    
    # Use synchronous client to send message via bot
    with httpx.Client() as client:
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
        
        # Send message to the channel using bot token
        response = client.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers={
                "Authorization": f"Bot {settings.discord_bot_token}",
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


def create_channel_handler(area: Area, params: dict, event: dict) -> None:
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
    from app.services.variable_resolver import resolve_variables
    
    guild_id = params.get("guild_id")
    name_template = params.get("name", "")
    channel_type = params.get("type", 0)  # 0 = text channel, 2 = voice channel
    
    if not guild_id or not name_template:
        error_msg = f"Discord create_channel missing required params: guild_id={guild_id}, name={bool(name_template)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    if not settings.discord_bot_token:
        error_msg = "Discord bot token not configured. Set DISCORD_BOT_TOKEN in .env file."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Resolve variables in channel name
    channel_name = resolve_variables(name_template, event)
    
    # Use synchronous client to create channel via bot
    with httpx.Client() as client:
        # Create the channel
        response = client.post(
            f"https://discord.com/api/v10/guilds/{guild_id}/channels",
            headers={
                "Authorization": f"Bot {settings.discord_bot_token}",
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
]
