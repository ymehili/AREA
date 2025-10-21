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
            
            mock_client.return_value.__enter__.return_value.get.side_effect = \
                Exception("Network error")

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
                "global_name": "Test User"
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

    def test_extract_message_with_attachments(self):
        """Test extracting data from message with attachments."""
        message = {
            "id": "msg123",
            "channel_id": "channel456",
            "content": "Check this out",
            "timestamp": "2023-01-01T00:00:00.000000+00:00",
            "author": {"id": "user789", "username": "testuser"},
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
        mock_db = Mock()
        mock_area = Mock(spec=Area)
        mock_area.id = 1
        mock_area.name = "Test Area"
        mock_area.user_id = "user123"
        
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
                "global_name": "Test User"
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
        mock_db = Mock()
        mock_area = Mock(spec=Area)
        mock_area.id = 1
        mock_area.name = "Test Area"
        mock_area.user_id = "user123"
        
        mock_db.merge.return_value = mock_area
        
        message = {
            "id": "msg123",
            "channel_id": "channel456",
            "content": "Test",
            "timestamp": "2023-01-01T00:00:00.000000+00:00",
            "author": {"id": "user789", "username": "testuser"},
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
        with patch("app.integrations.simple_plugins.discord_scheduler.SessionLocal") as mock_session, \
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
        with patch("app.integrations.simple_plugins.discord_scheduler.SessionLocal") as mock_session, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            # First call raises error, second call raises CancelledError to stop
            mock_sleep.side_effect = [
                None,  # First sleep succeeds
                asyncio.CancelledError()  # Second sleep stops the loop
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

                # Verify error was handled
                assert mock_sleep.call_count == 2
