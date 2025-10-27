"""Tests for Discord plugin actions."""

from __future__ import annotations

from unittest.mock import Mock, patch, MagicMock
import pytest
import httpx

from app.integrations.simple_plugins.discord_plugin import (
    send_message_handler,
    create_channel_handler,
)
from app.models.area import Area


class TestDiscordSendMessageHandler:
    """Test Discord send_message_handler action."""

    @pytest.fixture
    def mock_area(self):
        """Create a mock Area instance."""
        area = Mock(spec=Area)
        area.id = 1
        area.name = "Test Area"
        return area

    @pytest.fixture
    def base_params(self):
        """Base parameters for send_message."""
        return {
            "channel_id": "123456789012345678",
            "message": "Test message"
        }

    @pytest.fixture
    def event_data(self):
        """Sample event data."""
        return {
            "trigger": "test_trigger",
            "data": {"value": "test_value"}
        }

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_area, base_params, event_data):
        """Test successful message sending."""
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.discord_plugin.httpx.Client") as mock_client, \
             patch("app.services.variable_resolver.resolve_variables") as mock_resolve:
            
            mock_get_token.return_value = "test_bot_token"
            mock_resolve.side_effect = lambda template, event: template  # Return template as-is
            
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            # Should not raise any exception
            await send_message_handler(mock_area, base_params, event_data)

            # Verify the API call was made correctly
            mock_client.return_value.__enter__.return_value.post.assert_called_once()
            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            
            assert "https://discord.com/api/v10/channels/123456789012345678/messages" in call_args[0]
            assert call_args[1]["headers"]["Authorization"] == "Bot test_bot_token"
            assert call_args[1]["json"]["content"] == "Test message"

    @pytest.mark.asyncio
    async def test_send_message_with_variable_resolution(self, mock_area, base_params, event_data):
        """Test message sending with variable resolution."""
        base_params["message"] = "Hello {{data.value}}!"
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.discord_plugin.httpx.Client") as mock_client, \
             patch("app.services.variable_resolver.resolve_variables") as mock_resolve:
            
            mock_get_token.return_value = "test_bot_token"
            mock_resolve.return_value = "Hello test_value!"
            
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            await send_message_handler(mock_area, base_params, event_data)

            # Verify variable resolution was called
            mock_resolve.assert_called()
            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            assert call_args[1]["json"]["content"] == "Hello test_value!"

    @pytest.mark.asyncio
    async def test_send_message_with_image_attachment(self, mock_area, base_params, event_data):
        """Test message sending with image attachment."""
        base_params["attachment_url"] = "https://example.com/image.png"
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.discord_plugin.httpx.Client") as mock_client, \
             patch("app.services.variable_resolver.resolve_variables") as mock_resolve:
            
            mock_get_token.return_value = "test_bot_token"
            mock_resolve.side_effect = lambda template, event: template
            
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            await send_message_handler(mock_area, base_params, event_data)

            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            payload = call_args[1]["json"]
            
            assert "embeds" in payload
            assert payload["embeds"][0]["image"]["url"] == "https://example.com/image.png"

    @pytest.mark.asyncio
    async def test_send_message_with_video_attachment(self, mock_area, base_params, event_data):
        """Test message sending with video attachment."""
        base_params["attachment_url"] = "https://example.com/video.mp4"
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.discord_plugin.httpx.Client") as mock_client, \
             patch("app.services.variable_resolver.resolve_variables") as mock_resolve:
            
            mock_get_token.return_value = "test_bot_token"
            mock_resolve.side_effect = lambda template, event: template
            
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            await send_message_handler(mock_area, base_params, event_data)

            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            payload = call_args[1]["json"]
            
            assert "embeds" in payload
            assert payload["embeds"][0]["video"]["url"] == "https://example.com/video.mp4"

    @pytest.mark.asyncio
    async def test_send_message_with_non_media_attachment(self, mock_area, base_params, event_data):
        """Test message sending with non-image/video attachment URL."""
        base_params["attachment_url"] = "https://example.com/document.pdf"
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.discord_plugin.httpx.Client") as mock_client, \
             patch("app.services.variable_resolver.resolve_variables") as mock_resolve:
            
            mock_get_token.return_value = "test_bot_token"
            mock_resolve.side_effect = lambda template, event: template
            
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            await send_message_handler(mock_area, base_params, event_data)

            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            payload = call_args[1]["json"]
            
            # Should include URL in message content instead of embed
            assert "embeds" not in payload
            assert "https://example.com/document.pdf" in payload["content"]

    @pytest.mark.asyncio
    async def test_send_message_missing_channel_id(self, mock_area, event_data):
        """Test send_message with missing channel_id."""
        params = {"message": "Test message"}
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token:
            mock_get_token.return_value = "test_bot_token"
            
            with pytest.raises(ValueError) as exc_info:
                await send_message_handler(mock_area, params, event_data)
            
            assert "missing required params" in str(exc_info.value)
            assert "channel_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_missing_message(self, mock_area, event_data):
        """Test send_message with missing message."""
        params = {"channel_id": "102030405060708091"}
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token:
            mock_get_token.return_value = "test_bot_token"
            
            with pytest.raises(ValueError) as exc_info:
                await send_message_handler(mock_area, params, event_data)
            
            assert "missing required params" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_empty_message(self, mock_area, event_data):
        """Test send_message with empty message."""
        params = {"channel_id": "102030405060708091", "message": ""}
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token:
            mock_get_token.return_value = "test_bot_token"
            
            with pytest.raises(ValueError) as exc_info:
                await send_message_handler(mock_area, params, event_data)
            
            assert "missing required params" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_no_bot_token(self, mock_area, base_params, event_data):
        """Test send_message when bot token is not configured."""
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token:
            mock_get_token.return_value = None
            
            with pytest.raises(ValueError) as exc_info:
                await send_message_handler(mock_area, base_params, event_data)
            
            assert "bot token not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_http_error(self, mock_area, base_params, event_data):
        """Test send_message with HTTP error from Discord API."""
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.discord_plugin.httpx.Client") as mock_client, \
             patch("app.services.variable_resolver.resolve_variables") as mock_resolve:
            
            mock_get_token.return_value = "test_bot_token"
            mock_resolve.side_effect = lambda template, event: template
            
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "403 Forbidden",
                request=Mock(),
                response=Mock(text="Missing Access", status_code=403)
            )
            mock_response.text = "Missing Access"
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                await send_message_handler(mock_area, base_params, event_data)


class TestDiscordCreateChannelHandler:
    """Test Discord create_channel_handler action."""

    @pytest.fixture
    def mock_area(self):
        """Create a mock Area instance."""
        area = Mock(spec=Area)
        area.id = 1
        area.name = "Test Area"
        return area

    @pytest.fixture
    def base_params(self):
        """Base parameters for create_channel."""
        return {
            "guild_id": "123456789012345678",  # Valid Discord ID (18 digits)
            "name": "new-channel"
        }

    @pytest.fixture
    def event_data(self):
        """Sample event data."""
        return {
            "trigger": "test_trigger",
            "data": {"channel_name": "dynamic-channel"}
        }

    @pytest.mark.asyncio
    async def test_create_channel_success(self, mock_area, base_params, event_data):
        """Test successful channel creation."""
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.discord_plugin.httpx.Client") as mock_client, \
             patch("app.services.variable_resolver.resolve_variables") as mock_resolve:
            
            mock_get_token.return_value = "test_bot_token"
            mock_resolve.side_effect = lambda template, event: template
            
            mock_response = Mock()
            mock_response.json.return_value = {"id": "111111111", "name": "new-channel"}
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            # Should not raise any exception
            await create_channel_handler(mock_area, base_params, event_data)

            # Verify the API call was made correctly
            mock_client.return_value.__enter__.return_value.post.assert_called_once()
            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            
            assert "https://discord.com/api/v10/guilds/123456789012345678/channels" in call_args[0]
            assert call_args[1]["headers"]["Authorization"] == "Bot test_bot_token"
            assert call_args[1]["json"]["name"] == "new-channel"
            assert call_args[1]["json"]["type"] == 0  # Text channel

    @pytest.mark.asyncio
    async def test_create_channel_with_variable_resolution(self, mock_area, base_params, event_data):
        """Test channel creation with variable resolution."""
        base_params["name"] = "{{data.channel_name}}"
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.discord_plugin.httpx.Client") as mock_client, \
             patch("app.services.variable_resolver.resolve_variables") as mock_resolve:
            
            mock_get_token.return_value = "test_bot_token"
            mock_resolve.return_value = "dynamic-channel"
            
            mock_response = Mock()
            mock_response.json.return_value = {"id": "111111111", "name": "dynamic-channel"}
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            await create_channel_handler(mock_area, base_params, event_data)

            # Verify variable resolution was called
            mock_resolve.assert_called_once()
            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            assert call_args[1]["json"]["name"] == "dynamic-channel"

    @pytest.mark.asyncio
    async def test_create_channel_voice_type(self, mock_area, base_params, event_data):
        """Test voice channel creation."""
        base_params["type"] = 2  # Voice channel
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.discord_plugin.httpx.Client") as mock_client, \
             patch("app.services.variable_resolver.resolve_variables") as mock_resolve:
            
            mock_get_token.return_value = "test_bot_token"
            mock_resolve.side_effect = lambda template, event: template
            
            mock_response = Mock()
            mock_response.json.return_value = {"id": "111111111", "name": "new-channel", "type": 2}
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            await create_channel_handler(mock_area, base_params, event_data)

            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            assert call_args[1]["json"]["type"] == 2

    @pytest.mark.asyncio
    async def test_create_channel_missing_guild_id(self, mock_area, event_data):
        """Test create_channel with missing guild_id."""
        params = {"name": "new-channel"}
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token:
            mock_get_token.return_value = "test_bot_token"
            
            with pytest.raises(ValueError) as exc_info:
                await create_channel_handler(mock_area, params, event_data)
            
            assert "missing required params" in str(exc_info.value)
            assert "guild_id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_channel_missing_name(self, mock_area, event_data):
        """Test create_channel with missing name."""
        params = {"guild_id": "102030405060708091"}  # Valid Discord ID (17 digits)
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token:
            mock_get_token.return_value = "test_bot_token"
            
            with pytest.raises(ValueError) as exc_info:
                await create_channel_handler(mock_area, params, event_data)
            
            assert "missing required params" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_channel_empty_name(self, mock_area, event_data):
        """Test create_channel with empty name."""
        params = {"guild_id": "102030405060708091", "name": ""}  # Valid Discord ID (17 digits)
        
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token:
            mock_get_token.return_value = "test_bot_token"
            
            with pytest.raises(ValueError) as exc_info:
                await create_channel_handler(mock_area, params, event_data)
            
            assert "missing required params" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_channel_no_bot_token(self, mock_area, base_params, event_data):
        """Test create_channel when bot token is not configured."""
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token:
            mock_get_token.return_value = ""
            
            with pytest.raises(ValueError) as exc_info:
                await create_channel_handler(mock_area, base_params, event_data)
            
            assert "bot token not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_channel_http_error(self, mock_area, base_params, event_data):
        """Test create_channel with HTTP error from Discord API."""
        with patch("app.core.encryption.get_discord_bot_token") as mock_get_token, \
             patch("app.integrations.simple_plugins.discord_plugin.httpx.Client") as mock_client, \
             patch("app.services.variable_resolver.resolve_variables") as mock_resolve:
            
            mock_get_token.return_value = "test_bot_token"
            mock_resolve.side_effect = lambda template, event: template
            
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "403 Forbidden",
                request=Mock(),
                response=Mock(text="Missing Permissions", status_code=403)
            )
            mock_response.text = "Missing Permissions"
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                await create_channel_handler(mock_area, base_params, event_data)
