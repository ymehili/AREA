"""Tests for Discord message polling scheduler."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
import pytest

from app.integrations.simple_plugins.discord_scheduler import (
    _fetch_channel_messages,
    _extract_message_data,
    _fetch_due_discord_areas,
    _process_discord_trigger,
    discord_scheduler_task,
    start_discord_scheduler,
    stop_discord_scheduler,
    is_discord_scheduler_running,
    clear_discord_seen_state,
)
from app.models.area import Area


class TestFetchChannelMessages:
    """Test _fetch_channel_messages function."""

    def test_fetch_messages_success(self):
        """Test successful message fetching from Discord."""
        with patch("app.core.config.settings") as mock_settings, \
             patch("app.integrations.simple_plugins.discord_scheduler.httpx.Client") as mock_client:
            
            mock_settings.discord_bot_token = "test_bot_token"
            
            mock_response = Mock()
            mock_response.json.return_value = [
                {
                    "id": "msg1",
                    "content": "Hello",
                    "author": {"id": "user1", "username": "testuser"},
                    "channel_id": "123456789",
                    "timestamp": "2023-01-01T00:00:00.000000+00:00"
                }
            ]
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            messages = _fetch_channel_messages("123456789")

            assert len(messages) == 1
            assert messages[0]["id"] == "msg1"
            assert messages[0]["content"] == "Hello"

    def test_fetch_messages_no_bot_token(self):
        """Test fetching messages without bot token configured."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.discord_bot_token = None

            messages = _fetch_channel_messages("123456789")

            assert messages == []

    def test_fetch_messages_http_error(self):
        """Test handling HTTP error when fetching messages."""
        with patch("app.core.config.settings") as mock_settings, \
             patch("app.integrations.simple_plugins.discord_scheduler.httpx.Client") as mock_client:
            
            mock_settings.discord_bot_token = "test_bot_token"
            
            # Make the get method raise an HTTPError
            import httpx
            mock_client.return_value.__enter__.return_value.get.side_effect = \
                httpx.HTTPError("Network error")

            messages = _fetch_channel_messages("123456789")

            assert messages == []


class TestExtractMessageData:
    """Test _extract_message_data function."""

    def test_extract_basic_message_data(self):
        """Test extracting data from a basic Discord message."""
        message = {
            "id": "msg123",
            "channel_id": "channel456",
            "content": "Test message",
            "timestamp": "2023-01-01T00:00:00.000000+00:00",
            "author": {
                "id": "user789",
                "username": "testuser",
                "discriminator": "1234",
                "global_name": "Test User",
                "bot": False
            },
            "mentions": [],
            "attachments": [],
            "embeds": []
        }

        data = _extract_message_data(message)

        assert data["id"] == "msg123"
        assert data["channel_id"] == "channel456"
        assert data["content"] == "Test message"
        assert data["author_id"] == "user789"
        assert data["author_username"] == "testuser"
        assert data["author_discriminator"] == "1234"
        assert data["author_global_name"] == "Test User"
        assert data["author_is_bot"] == False

    def test_extract_message_with_attachments(self):
        """Test extracting data from message with attachments."""
        message = {
            "id": "msg123",
            "channel_id": "channel456",
            "content": "Check this out",
            "timestamp": "2023-01-01T00:00:00.000000+00:00",
            "author": {"id": "user789", "username": "testuser", "bot": False},
            "mentions": [],
            "attachments": [
                {
                    "id": "att1",
                    "filename": "image.png",
                    "url": "https://cdn.discord.com/image.png",
                    "content_type": "image/png"
                }
            ],
            "embeds": []
        }

        data = _extract_message_data(message)

        assert len(data["attachments"]) == 1
        assert data["attachments"][0]["filename"] == "image.png"
        assert data["attachments"][0]["url"] == "https://cdn.discord.com/image.png"
        assert data["author_is_bot"] == False

    def test_extract_message_missing_fields(self):
        """Test extracting data from message with missing fields."""
        message = {
            "id": "msg123",
            "author": {}
        }

        data = _extract_message_data(message)

        assert data["id"] == "msg123"
        assert data["content"] == ""
        assert data["author_id"] == ""
        assert data["author_username"] == ""
        assert data["author_is_bot"] == False  # Defaults to False when missing
        assert data["attachments"] == []


class TestFetchDueDiscordAreas:
    """Test _fetch_due_discord_areas function."""

    def test_fetch_enabled_discord_areas(self):
        """Test fetching only enabled Discord areas."""
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        area1 = Mock(spec=Area)
        area1.id = 1
        area1.enabled = True
        area1.trigger_service = "discord"
        
        mock_query.all.return_value = [area1]

        areas = _fetch_due_discord_areas(mock_db)

        assert len(areas) == 1
        assert areas[0].id == 1


class TestProcessDiscordTrigger:
    """Test _process_discord_trigger function."""

    @pytest.mark.asyncio
    async def test_process_trigger_success(self):
        """Test successful processing of Discord trigger."""
        from uuid import uuid4
        
        mock_db = Mock()
        mock_area = Mock(spec=Area)
        mock_area.id = uuid4()
        mock_area.name = "Test Area"
        mock_area.user_id = uuid4()
        
        mock_db.merge.return_value = mock_area
        
        message = {
            "id": "msg123",
            "channel_id": "channel456",
            "content": "Test message",
            "timestamp": "2023-01-01T00:00:00.000000+00:00",
            "author": {
                "id": "user789",
                "username": "testuser",
                "discriminator": "1234",
                "global_name": "Test User",
                "bot": False
            },
            "mentions": [],
            "attachments": [],
            "embeds": []
        }

        now = datetime.now(timezone.utc)

        with patch("app.integrations.simple_plugins.discord_scheduler.create_execution_log") as mock_create_log, \
             patch("app.integrations.simple_plugins.discord_scheduler.execute_area") as mock_execute:
            
            mock_execution_log = Mock()
            mock_create_log.return_value = mock_execution_log
            
            mock_execute.return_value = {
                "status": "success",
                "steps_executed": 2,
                "execution_log": []
            }

            await _process_discord_trigger(mock_db, mock_area, message, now)

            # Verify execution log was created and updated
            mock_create_log.assert_called_once()
            assert mock_execution_log.status == "Success"
            mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_process_trigger_execution_failure(self):
        """Test processing trigger when area execution fails."""
        from uuid import uuid4
        
        mock_db = Mock()
        mock_area = Mock(spec=Area)
        mock_area.id = uuid4()
        mock_area.name = "Test Area"
        mock_area.user_id = uuid4()
        
        mock_db.merge.return_value = mock_area
        
        message = {
            "id": "msg123",
            "channel_id": "channel456",
            "content": "Test",
            "timestamp": "2023-01-01T00:00:00.000000+00:00",
            "author": {"id": "user789", "username": "testuser", "bot": False},
            "mentions": [],
            "attachments": [],
            "embeds": []
        }

        now = datetime.now(timezone.utc)

        with patch("app.integrations.simple_plugins.discord_scheduler.create_execution_log") as mock_create_log, \
             patch("app.integrations.simple_plugins.discord_scheduler.execute_area") as mock_execute:
            
            mock_execution_log = Mock()
            mock_create_log.return_value = mock_execution_log
            
            mock_execute.side_effect = Exception("Execution failed")

            # Should not raise exception
            await _process_discord_trigger(mock_db, mock_area, message, now)

            # Verify execution log was updated with failure
            assert mock_execution_log.status == "Failed"
            assert "Execution failed" in mock_execution_log.error_message


class TestDiscordSchedulerLifecycle:
    """Test Discord scheduler lifecycle functions."""

    def test_start_discord_scheduler(self):
        """Test starting the Discord scheduler."""
        clear_discord_seen_state()
        stop_discord_scheduler()  # Ensure stopped first
        
        # We can't easily test the actual scheduler in unit tests without a running event loop
        # So we just verify the functions exist and don't crash
        assert callable(start_discord_scheduler)
        assert callable(stop_discord_scheduler)
        assert callable(is_discord_scheduler_running)

    def test_clear_discord_seen_state(self):
        """Test clearing Discord seen state."""
        # Should not raise any exception
        clear_discord_seen_state()


class TestDiscordSchedulerTask:
    """Test discord_scheduler_task main loop."""

    @pytest.mark.asyncio
    async def test_scheduler_task_cancellation(self):
        """Test that scheduler task handles cancellation gracefully."""
        with patch("app.db.session.SessionLocal") as mock_session, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            # Make sleep raise CancelledError after first call
            mock_sleep.side_effect = asyncio.CancelledError()

            # Should not raise exception, but exit gracefully
            await discord_scheduler_task()

            # Verify sleep was called
            mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_scheduler_task_handles_errors(self):
        """Test that scheduler task handles errors and continues."""
        with patch("app.db.session.SessionLocal") as mock_session, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            # Setup sleep side effects: first for regular polling, second for error backoff, third to cancel
            mock_sleep.side_effect = [
                None,  # First sleep (regular polling interval)
                None,  # Second sleep (error backoff)
                asyncio.CancelledError()  # Third sleep stops the loop
            ]
            
            mock_db = Mock()
            mock_db.__enter__ = Mock(return_value=mock_db)
            mock_db.__exit__ = Mock(return_value=None)
            mock_session.return_value = mock_db
            
            # Make _fetch_due_discord_areas raise error
            with patch("app.integrations.simple_plugins.discord_scheduler._fetch_due_discord_areas") as mock_fetch:
                mock_fetch.side_effect = Exception("Database error")

                # Should not raise exception
                await discord_scheduler_task()

                # Verify error was handled and backoff was called
                assert mock_sleep.call_count == 3

    @pytest.mark.asyncio
    async def test_scheduler_processes_areas_with_new_message(self):
        """Test that scheduler processes Discord areas with new messages."""
        from uuid import uuid4
        from app.integrations.simple_plugins import discord_scheduler
        
        mock_area = Mock(spec=Area)
        area_id = uuid4()
        mock_area.id = area_id
        mock_area.user_id = uuid4()
        mock_area.trigger_action = "new_message_in_channel"
        mock_area.trigger_params = {"channel_id": "123456789"}

        message = {
            "id": "msg123",
            "channel_id": "123456789",
            "content": "Test message",
            "timestamp": "2023-01-01T00:00:00.000000+00:00",
            "author": {
                "id": "user789",
                "username": "testuser",
                "discriminator": "1234",
                "global_name": "Test User",
                "bot": False
            },
            "mentions": [],
            "attachments": [],
            "embeds": []
        }

        # Reset the seen messages state - make sure the message is already in the seen set
        # so we can add a NEW message that will trigger processing
        area_id_str = str(area_id)
        discord_scheduler._last_seen_messages[area_id_str] = set()

        with patch("app.db.session.SessionLocal") as mock_session, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch("app.integrations.simple_plugins.discord_scheduler._fetch_due_discord_areas") as mock_fetch, \
             patch("app.integrations.simple_plugins.discord_scheduler._fetch_channel_messages") as mock_messages, \
             patch("app.integrations.simple_plugins.discord_scheduler._process_discord_trigger") as mock_process:
            
            # First sleep returns immediately, second sleep cancels
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            
            mock_db = Mock()
            mock_db.__enter__ = Mock(return_value=mock_db)
            mock_db.__exit__ = Mock(return_value=None)
            mock_session.return_value = mock_db
            
            mock_fetch.return_value = [mock_area]
            # Return empty list first time (to initialize seen set), then return the message on second call
            # But since we cancel on second sleep, we need to return the message on first call
            # and ensure it's NOT in the seen set initially (which we did above)
            # However, the scheduler initializes the seen set with ALL messages on first run
            # So we need to mock it differently - return the message AFTER seen set is initialized
            
            # Solution: Pre-populate the seen set with an old message, then return a new one
            old_message_id = "old_msg_id"
            discord_scheduler._last_seen_messages[area_id_str] = {old_message_id}
            mock_messages.return_value = [message]

            await discord_scheduler_task()

            # Verify area was processed
            mock_process.assert_called_once()
            
            # Clean up
            if area_id_str in discord_scheduler._last_seen_messages:
                del discord_scheduler._last_seen_messages[area_id_str]

    @pytest.mark.asyncio
    async def test_scheduler_skips_areas_without_channel_id(self):
        """Test that scheduler skips areas without channel_id."""
        from uuid import uuid4
        
        mock_area = Mock(spec=Area)
        mock_area.id = uuid4()
        mock_area.user_id = uuid4()
        mock_area.trigger_action = "new_message_in_channel"
        mock_area.trigger_params = {}  # Missing channel_id

        with patch("app.db.session.SessionLocal") as mock_session, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch("app.integrations.simple_plugins.discord_scheduler._fetch_due_discord_areas") as mock_fetch, \
             patch("app.integrations.simple_plugins.discord_scheduler._fetch_channel_messages") as mock_messages, \
             patch("app.integrations.simple_plugins.discord_scheduler._process_discord_trigger") as mock_process:
            
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            
            mock_db = Mock()
            mock_db.__enter__ = Mock(return_value=mock_db)
            mock_db.__exit__ = Mock(return_value=None)
            mock_session.return_value = mock_db
            
            mock_fetch.return_value = [mock_area]

            await discord_scheduler_task()

            # Verify messages were not fetched and area was not processed
            mock_messages.assert_not_called()
            mock_process.assert_not_called()

    @pytest.mark.asyncio
    async def test_scheduler_filters_bot_messages(self):
        """Test that scheduler filters out messages from bots to prevent infinite loops."""
        from uuid import uuid4
        from app.integrations.simple_plugins import discord_scheduler
        
        mock_area = Mock(spec=Area)
        area_id = uuid4()
        mock_area.id = area_id
        mock_area.user_id = uuid4()
        mock_area.trigger_action = "new_message_in_channel"
        mock_area.trigger_params = {"channel_id": "123456789"}

        # Create a human message and a bot message
        human_message = {
            "id": "human_msg",
            "channel_id": "123456789",
            "content": "Hello from human",
            "timestamp": "2023-01-01T00:00:00.000000+00:00",
            "author": {
                "id": "user789",
                "username": "human_user",
                "bot": False
            },
            "mentions": [],
            "attachments": [],
            "embeds": []
        }

        bot_message = {
            "id": "bot_msg",
            "channel_id": "123456789",
            "content": "Hello from bot",
            "timestamp": "2023-01-01T00:01:00.000000+00:00",
            "author": {
                "id": "bot123",
                "username": "my_bot",
                "bot": True
            },
            "mentions": [],
            "attachments": [],
            "embeds": []
        }

        area_id_str = str(area_id)
        # Pre-populate with an old message to avoid initialization logic
        discord_scheduler._last_seen_messages[area_id_str] = {"old_msg"}

        with patch("app.db.session.SessionLocal") as mock_session, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch("app.integrations.simple_plugins.discord_scheduler._fetch_due_discord_areas") as mock_fetch, \
             patch("app.integrations.simple_plugins.discord_scheduler._fetch_channel_messages") as mock_messages, \
             patch("app.integrations.simple_plugins.discord_scheduler._process_discord_trigger") as mock_process:
            
            # First sleep returns immediately, second sleep cancels
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            
            mock_db = Mock()
            mock_db.__enter__ = Mock(return_value=mock_db)
            mock_db.__exit__ = Mock(return_value=None)
            mock_session.return_value = mock_db
            
            mock_fetch.return_value = [mock_area]
            # Return both human and bot messages
            mock_messages.return_value = [bot_message, human_message]

            await discord_scheduler_task()

            # Verify only the human message was processed (bot message filtered out)
            assert mock_process.call_count == 1
            # Get the message that was passed to _process_discord_trigger
            processed_message = mock_process.call_args[0][2]
            assert processed_message["id"] == "human_msg"
            assert processed_message["author"]["bot"] == False
            
            # Clean up
            if area_id_str in discord_scheduler._last_seen_messages:
                del discord_scheduler._last_seen_messages[area_id_str]


class TestExtractMessageData:
    """Tests for _extract_message_data function."""

    def test_extract_full_message_data(self):
        """Test extracting all data from a complete Discord message."""
        from app.integrations.simple_plugins.discord_scheduler import _extract_message_data
        
        message = {
            "id": "msg123",
            "channel_id": "channel456",
            "content": "Test message content",
            "timestamp": "2023-01-01T00:00:00.000000+00:00",
            "author": {
                "id": "user789",
                "username": "testuser",
                "discriminator": "1234",
                "global_name": "Test User",
                "bot": False
            },
            "mentions": [{"id": "mentioned_user_1"}, {"id": "mentioned_user_2"}],
            "attachments": [
                {
                    "id": "att1",
                    "filename": "image.png",
                    "url": "https://cdn.discord.com/image.png",
                    "content_type": "image/png"
                }
            ],
            "embeds": [{"title": "Embed Title"}]
        }

        result = _extract_message_data(message)

        assert result["id"] == "msg123"
        assert result["channel_id"] == "channel456"
        assert result["content"] == "Test message content"
        assert result["timestamp"] == "2023-01-01T00:00:00.000000+00:00"
        assert result["author_id"] == "user789"
        assert result["author_username"] == "testuser"
        assert result["author_discriminator"] == "1234"
        assert result["author_global_name"] == "Test User"
        assert result["author_is_bot"] == False
        assert len(result["mentions"]) == 2
        assert len(result["attachments"]) == 1
        assert result["attachments"][0]["filename"] == "image.png"
        assert len(result["embeds"]) == 1

    def test_extract_minimal_message_data(self):
        """Test extracting data from a minimal Discord message."""
        from app.integrations.simple_plugins.discord_scheduler import _extract_message_data
        
        message = {
            "id": "msg123",
        }

        result = _extract_message_data(message)

        assert result["id"] == "msg123"
        assert result["channel_id"] is None
        assert result["content"] == ""
        assert result["timestamp"] == ""
        assert result["author_id"] == ""
        assert result["author_is_bot"] == False
        assert result["mentions"] == []
        assert result["attachments"] == []
        assert result["embeds"] == []

    def test_extract_bot_message_data(self):
        """Test extracting data from a bot message."""
        from app.integrations.simple_plugins.discord_scheduler import _extract_message_data
        
        message = {
            "id": "bot_msg123",
            "channel_id": "channel456",
            "content": "I am a bot",
            "timestamp": "2023-01-01T00:00:00.000000+00:00",
            "author": {
                "id": "bot123",
                "username": "coolbot",
                "bot": True
            },
            "mentions": [],
            "attachments": [],
            "embeds": []
        }

        result = _extract_message_data(message)

        assert result["id"] == "bot_msg123"
        assert result["author_id"] == "bot123"
        assert result["author_username"] == "coolbot"
        assert result["author_is_bot"] == True
