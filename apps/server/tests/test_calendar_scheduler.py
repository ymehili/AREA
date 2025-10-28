"""Tests for Google Calendar scheduler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from typing import Dict
from google.auth.exceptions import RefreshError

from app.integrations.simple_plugins.calendar_scheduler import (
    _get_calendar_service,
    _fetch_events,
    _extract_event_data,
    _fetch_due_calendar_areas,
    calendar_scheduler_task,
    _fetch_events_for_trigger,
    _process_calendar_trigger,
    start_calendar_scheduler,
    stop_calendar_scheduler,
    is_calendar_scheduler_running,
    clear_calendar_seen_state,
    cleanup_old_seen_events
)
from app.models.area import Area
from app.models.service_connection import ServiceConnection


class TestCalendarScheduler:
    """Test Google Calendar scheduler functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_service_connection(self):
        """Create a mock service connection."""
        connection = MagicMock(spec=ServiceConnection)
        connection.id = "test_connection_id"
        connection.user_id = "test_user_id"
        connection.service_name = "google_calendar"
        connection.encrypted_access_token = "encrypted_access_token"
        connection.encrypted_refresh_token = "encrypted_refresh_token"
        return connection

    def test_get_calendar_service_success(self, mock_db, mock_service_connection):
        """Test getting authenticated Google Calendar service."""
        from unittest.mock import ANY
        from google.oauth2.credentials import Credentials
        with patch("app.integrations.simple_plugins.calendar_scheduler.get_service_connection_by_user_and_service") as mock_get_conn:
            with patch("app.integrations.simple_plugins.calendar_scheduler.decrypt_token") as mock_decrypt:
                with patch("app.integrations.simple_plugins.calendar_scheduler.Request") as mock_request:
                    with patch("app.integrations.simple_plugins.calendar_scheduler.build") as mock_build:
                        from app.core.config import settings
                        mock_get_conn.return_value = mock_service_connection
                        mock_decrypt.side_effect = ["decrypted_access", "decrypted_refresh"]
                        # Create a real Credentials object instead of mocking it to avoid the super() error
                        mock_creds = MagicMock(spec=Credentials)
                        mock_creds.token = "decrypted_access"
                        mock_creds.refresh_token = "decrypted_refresh"
                        mock_creds.expired = False
                        mock_creds.expiry = None
                        type(mock_creds).valid = True
                        # Set up the expected attributes
                        mock_request.return_value = MagicMock()
                        with patch("app.integrations.simple_plugins.calendar_scheduler.Credentials") as mock_creds_class:
                            mock_creds_class.return_value = mock_creds
                            mock_service = MagicMock()
                            mock_build.return_value = mock_service
                            service = _get_calendar_service("test_user_id", mock_db)
                            # Verify that the service was properly built
                            mock_get_conn.assert_called_once_with(mock_db, "test_user_id", "google_calendar")
                            assert mock_decrypt.call_count == 2
                            # Check that build was called with the expected parameters
                            mock_build.assert_called_once_with('calendar', 'v3', credentials=mock_creds)

    def test_get_calendar_service_no_connection(self, mock_db):
        """Test getting calendar service when no connection exists."""
        with patch("app.integrations.simple_plugins.calendar_scheduler.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.return_value = None

            service = _get_calendar_service("test_user_id", mock_db)

            assert service is None

    @pytest.mark.asyncio
    async def test_fetch_events_success(self):
        """Test fetching events from Google Calendar API."""
        mock_service = MagicMock()
        mock_events_result = {
            'items': [
                {
                    'id': 'event1',
                    'summary': 'Test Event',
                    'start': {'dateTime': '2023-01-01T10:00:00Z'},
                    'end': {'dateTime': '2023-01-01T11:00:00Z'}
                }
            ]
        }
        mock_service.events().list().execute.return_value = mock_events_result

        events = _fetch_events(mock_service, "2023-01-01T00:00:00Z", "2023-01-02T00:00:00Z")

        assert len(events) == 1
        assert events[0]['id'] == 'event1'
        assert events[0]['summary'] == 'Test Event'

    @pytest.mark.asyncio
    async def test_fetch_events_with_http_error(self):
        """Test fetching events when an HTTP error occurs."""
        from googleapiclient.errors import HttpError
        import httplib2
        mock_service = MagicMock()
        mock_service.events().list().execute.side_effect = HttpError(
            httplib2.Response({'status': 403}),
            b'{"error": {"message": "Access denied"}}'
        )

        events = _fetch_events(mock_service, "2023-01-01T00:00:00Z", "2023-01-02T00:00:00Z")

        assert events == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_fetch_events_with_refresh_error(self):
        """Test fetching events when a refresh error occurs."""
        mock_service = MagicMock()
        mock_service.events().list().execute.side_effect = RefreshError("Token expired")

        events = _fetch_events(mock_service, "2023-01-01T00:00:00Z", "2023-01-02T00:00:00Z")

        assert events == []  # Should return empty list on refresh error

    def test_extract_event_data(self):
        """Test extracting event data from a Google Calendar event."""
        full_event = {
            'id': 'event123',
            'summary': 'Team Meeting',
            'description': 'Weekly team sync',
            'location': 'Conference Room A',
            'start': {'dateTime': '2023-01-01T10:00:00Z'},
            'end': {'dateTime': '2023-01-01T11:00:00Z'},
            'timeZone': 'UTC',
            'attendees': [
                {'email': 'user1@example.com'},
                {'email': 'user2@example.com'}
            ],
            'organizer': {'email': 'organizer@example.com'},
            'status': 'confirmed',
            'htmlLink': 'https://calendar.google.com/event123',
            'created': '2022-12-28T15:30:00Z',
            'updated': '2022-12-30T09:15:00Z'
        }

        extracted = _extract_event_data(full_event)

        assert extracted['id'] == 'event123'
        assert extracted['summary'] == 'Team Meeting'
        assert extracted['location'] == 'Conference Room A'
        assert extracted['start_time'] == '2023-01-01T10:00:00Z'
        assert extracted['end_time'] == '2023-01-01T11:00:00Z'
        assert extracted['timezone'] == 'UTC'
        assert extracted['attendees'] == ['user1@example.com', 'user2@example.com']
        assert extracted['organizer'] == 'organizer@example.com'
        assert extracted['status'] == 'confirmed'
        assert extracted['html_link'] == 'https://calendar.google.com/event123'
        assert extracted['is_all_day'] is False

    def test_extract_event_data_all_day(self):
        """Test extracting event data for an all-day event."""
        all_day_event = {
            'id': 'event456',
            'summary': 'Public Holiday',
            'start': {'date': '2023-01-01'},  # All-day event
            'end': {'date': '2023-01-02'},
            'attendees': [],
            'organizer': {}
        }

        extracted = _extract_event_data(all_day_event)

        assert extracted['id'] == 'event456'
        assert extracted['summary'] == 'Public Holiday'
        assert extracted['start_time'] == '2023-01-01'  # Date instead of datetime
        assert extracted['is_all_day'] is True

    def test_fetch_due_calendar_areas(self, mock_db):
        """Test fetching enabled areas with Google Calendar triggers."""
        mock_area = MagicMock(spec=Area)
        mock_area.id = "test_area_id"
        mock_area.trigger_service = "google_calendar"
        mock_area.enabled = True
        
        # Mock the query chain properly
        mock_query = MagicMock()
        mock_filtered_query = MagicMock()
        mock_query.filter.return_value = mock_filtered_query
        mock_filtered_query.all.return_value = [mock_area]
        mock_db.query.return_value = mock_query

        areas = _fetch_due_calendar_areas(mock_db)

        assert areas == [mock_area]
        mock_db.query.assert_called_once_with(Area)
        # Check that the filter is called with the correct conditions
        mock_query.filter.assert_called_once()
        # The filter should check for enabled=True and trigger_service='google_calendar'

    @pytest.mark.asyncio
    async def test_fetch_events_for_trigger_event_created(self):
        """Test fetching events for 'event_created' trigger."""
        mock_service = MagicMock()
        mock_area = MagicMock(spec=Area)
        mock_area.trigger_action = "event_created"
        mock_area.trigger_params = {}
        now = datetime.now(timezone.utc)

        with patch("app.integrations.simple_plugins.calendar_scheduler._fetch_events") as mock_fetch:
            mock_fetch.return_value = []
            events = await _fetch_events_for_trigger(mock_service, mock_area, now)

            assert events == []
            # Should fetch with time range of now to 30 days later
            mock_fetch.assert_called_once()
            args, kwargs = mock_fetch.call_args
            assert args[1] == now.isoformat()  # time_min
            expected_time_max = (now + timedelta(days=30)).isoformat()
            assert args[2] == expected_time_max  # time_max

    @pytest.mark.asyncio
    async def test_fetch_events_for_trigger_event_starting_soon(self):
        """Test fetching events for 'event_starting_soon' trigger."""
        mock_service = MagicMock()
        mock_area = MagicMock(spec=Area)
        mock_area.trigger_action = "event_starting_soon"
        mock_area.trigger_params = {"minutes_before": 30}
        now = datetime.now(timezone.utc)

        with patch("app.integrations.simple_plugins.calendar_scheduler._fetch_events") as mock_fetch:
            mock_fetch.return_value = []
            events = await _fetch_events_for_trigger(mock_service, mock_area, now)

            assert events == []
            # Should fetch with time range of now to now + minutes_before + 1
            mock_fetch.assert_called_once()
            args, kwargs = mock_fetch.call_args
            assert args[1] == now.isoformat()  # time_min
            expected_time_max = (now + timedelta(minutes=31)).isoformat()  # 30 + 1
            assert args[2] == expected_time_max  # time_max

    @pytest.mark.asyncio
    async def test_process_calendar_trigger_success(self, mock_db):
        """Test processing a calendar trigger successfully."""
        from uuid import UUID
        import uuid
        
        # Generate a proper UUID for the area
        area_uuid = uuid.uuid4()
        mock_area = MagicMock(spec=Area)
        mock_area.id = area_uuid
        mock_area.name = "Test Calendar Area"
        mock_area.user_id = uuid.uuid4()  # Also use proper UUID for user_id
        mock_cal_event = {
            'id': 'event123',
            'summary': 'Test Event',
            'start': {'dateTime': '2023-01-01T10:00:00Z'},
            'end': {'dateTime': '2023-01-01T11:00:00Z'}
        }
        now = datetime.now(timezone.utc)

        with patch("app.integrations.simple_plugins.calendar_scheduler.create_execution_log") as mock_create_log:
            with patch("app.integrations.simple_plugins.calendar_scheduler.execute_area") as mock_execute:
                mock_log = MagicMock()
                mock_create_log.return_value = mock_log
                mock_execute.return_value = {"status": "success", "steps_executed": 2}
                mock_db.merge.return_value = mock_area  # Mock the merge method

                await _process_calendar_trigger(mock_db, mock_area, mock_cal_event, now)

                # Verify execution log was created and updated
                mock_create_log.assert_called_once()
                assert mock_log.status == "Success"
                assert mock_log.output == "Calendar trigger executed: 2 step(s)"
                assert mock_log.error_message is None
                mock_db.commit.assert_called()

                # Verify area execution was called
                mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_calendar_trigger_failure(self, mock_db):
        """Test processing a calendar trigger when execution fails."""
        import uuid
        
        # Generate proper UUIDs
        area_uuid = uuid.uuid4()
        mock_area = MagicMock(spec=Area)
        mock_area.id = area_uuid
        mock_area.name = "Test Calendar Area"
        mock_area.user_id = uuid.uuid4()  # Also use proper UUID for user_id
        mock_cal_event = {
            'id': 'event123',
            'summary': 'Test Event',
            'start': {'dateTime': '2023-01-01T10:00:00Z'},
            'end': {'dateTime': '2023-01-01T11:00:00Z'}
        }
        now = datetime.now(timezone.utc)

        with patch("app.integrations.simple_plugins.calendar_scheduler.create_execution_log") as mock_create_log:
            with patch("app.integrations.simple_plugins.calendar_scheduler.execute_area") as mock_execute:
                mock_log = MagicMock()
                mock_create_log.return_value = mock_log
                mock_execute.side_effect = Exception("Execution failed")
                mock_db.merge.return_value = mock_area  # Mock the merge method

                await _process_calendar_trigger(mock_db, mock_area, mock_cal_event, now)

                # Verify execution log was created and updated with failure
                mock_create_log.assert_called_once()
                assert mock_log.status == "Failed"
                assert "Execution failed" in mock_log.error_message
                mock_db.commit.assert_called()

    def test_scheduler_start_stop_functions(self):
        """Test scheduler start, stop, and status functions."""
        # Initially, scheduler should not be running
        assert not is_calendar_scheduler_running()

        # Start should work
        start_calendar_scheduler()
        # This test doesn't actually start a task since there would be no event loop,
        # but we're testing the logic path

        # Stop should work
        stop_calendar_scheduler()

        # After stopping, status should show not running
        assert not is_calendar_scheduler_running()

    def test_clear_calendar_seen_state(self):
        """Test clearing the in-memory seen events state."""
        from app.integrations.simple_plugins.calendar_scheduler import _last_seen_events
        # Add some dummy data to the global state
        _last_seen_events["test_area"] = {"event1", "event2"}
        
        # Clear the state
        clear_calendar_seen_state()
        
        # Verify it's empty
        assert _last_seen_events == {}

    def test_cleanup_old_seen_events(self):
        """Test cleaning up old event IDs from memory."""
        from app.integrations.simple_plugins.calendar_scheduler import _last_seen_events
        # Add some dummy data to the global state with a large set
        _last_seen_events.clear()
        area_id = "test_area_1"
        _last_seen_events[area_id] = {f"event{i}" for i in range(150)}  # More than 10 * max_age_hours (default 24)

        # Run cleanup with max_age_hours=10, which means max_events_per_area = 100
        removed_count = cleanup_old_seen_events(max_age_hours=10)

        # Verify that events for that area were cleared
        assert removed_count == 150
        assert _last_seen_events[area_id] == set()  # Should be empty after cleanup

    def test_cleanup_old_seen_events_no_cleanup_needed(self):
        """Test that cleanup doesn't remove events when not needed."""
        from app.integrations.simple_plugins.calendar_scheduler import _last_seen_events
        # Add some dummy data to the global state with a small set
        _last_seen_events.clear()
        area_id = "test_area_2"
        _last_seen_events[area_id] = {"event1", "event2", "event3"}  # Less than 10 * max_age_hours

        # Run cleanup
        removed_count = cleanup_old_seen_events(max_age_hours=10)

        # Verify that nothing was removed
        assert removed_count == 0
        assert len(_last_seen_events[area_id]) == 3