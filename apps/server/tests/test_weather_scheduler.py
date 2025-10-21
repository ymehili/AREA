"""
Tests for Weather scheduler functionality.
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from uuid import uuid4

from app.models.area import Area
from app.integrations.simple_plugins.weather_scheduler import (
    _fetch_weather_data,
    _fetch_due_weather_areas,
    _get_weather_api_key,
    _extract_weather_variables,
    _check_temperature_threshold,
    _check_weather_condition,
    _process_weather_trigger,
    weather_scheduler_task,
    start_weather_scheduler,
    stop_weather_scheduler,
    is_weather_scheduler_running,
    clear_weather_state,
    _last_weather_state,
)


class TestFetchWeatherData:
    """Tests for _fetch_weather_data function."""

    def test_fetch_weather_success(self):
        """Test successful weather data fetch."""
        with patch("app.integrations.simple_plugins.weather_scheduler.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "main": {
                    "temp": 20.5,
                    "feels_like": 19.0,
                    "temp_min": 18.0,
                    "temp_max": 22.0,
                    "pressure": 1013,
                    "humidity": 65
                },
                "weather": [
                    {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d"
                    }
                ],
                "wind": {
                    "speed": 3.5,
                    "deg": 180
                },
                "name": "Paris"
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = _fetch_weather_data("test_api_key", "Paris")

            assert result is not None
            assert result["main"]["temp"] == 20.5
            assert result["weather"][0]["main"] == "Clear"
            assert result["name"] == "Paris"

    def test_fetch_weather_http_error(self):
        """Test handling HTTP error when fetching weather."""
        with patch("app.integrations.simple_plugins.weather_scheduler.httpx.Client") as mock_client:
            import httpx
            mock_client.return_value.__enter__.return_value.get.side_effect = \
                httpx.HTTPError("API error")

            result = _fetch_weather_data("test_api_key", "InvalidCity")

            assert result is None

    def test_fetch_weather_no_api_key(self):
        """Test fetch weather with no API key."""
        result = _fetch_weather_data(None, "Paris")
        assert result is None

    def test_fetch_weather_no_location(self):
        """Test fetch weather with no location."""
        result = _fetch_weather_data("test_api_key", None)
        assert result is None





class TestFetchDueWeatherAreas:
    """Tests for _fetch_due_weather_areas function."""

    def test_fetch_weather_areas(self):
        """Test fetching weather areas from database."""
        mock_db = Mock()
        mock_area1 = Mock(spec=Area)
        mock_area1.id = uuid4()
        mock_area1.enabled = True
        
        mock_area2 = Mock(spec=Area)
        mock_area2.id = uuid4()
        mock_area2.enabled = True
        
        # Setup the mock query chain properly
        # The actual code does: db.query(Area).filter(condition1, condition2).all()
        # So we need: query -> filter -> all
        mock_filter = Mock()
        mock_filter.all.return_value = [mock_area1, mock_area2]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_filter
        
        mock_db.query.return_value = mock_query

        areas = _fetch_due_weather_areas(mock_db)

        assert len(areas) == 2
        assert areas[0] == mock_area1
        assert areas[1] == mock_area2





class TestWeatherSchedulerTask:
    """Tests for weather_scheduler_task function."""

    @pytest.mark.asyncio
    async def test_scheduler_task_cancellation(self):
        """Test that scheduler task handles cancellation gracefully."""
        with patch("app.db.session.SessionLocal") as mock_session, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            # Make sleep raise CancelledError after first call
            mock_sleep.side_effect = asyncio.CancelledError()

            # Should not raise exception, but exit gracefully
            await weather_scheduler_task()

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
            
            # Make _fetch_due_weather_areas raise error
            with patch("app.integrations.simple_plugins.weather_scheduler._fetch_due_weather_areas") as mock_fetch:
                mock_fetch.side_effect = Exception("Database error")

                # Should not raise exception
                await weather_scheduler_task()

                # Verify error was handled and backoff was called
                assert mock_sleep.call_count == 3


class TestGetWeatherApiKey:
    """Tests for _get_weather_api_key function."""

    def test_get_weather_api_key_success(self):
        """Test successful API key retrieval."""
        user_id = "test-user-id"
        mock_db = Mock()
        mock_connection = Mock()
        mock_connection.encrypted_access_token = b"encrypted_key"

        with patch("app.integrations.simple_plugins.weather_scheduler.get_service_connection_by_user_and_service") as mock_get_conn, \
             patch("app.integrations.simple_plugins.weather_scheduler.decrypt_token") as mock_decrypt:
            
            mock_get_conn.return_value = mock_connection
            mock_decrypt.return_value = "decrypted_api_key"

            result = _get_weather_api_key(user_id, mock_db)

            assert result == "decrypted_api_key"
            mock_get_conn.assert_called_once_with(mock_db, user_id, "weather")

    def test_get_weather_api_key_no_connection(self):
        """Test API key retrieval when no connection exists."""
        user_id = "test-user-id"
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.weather_scheduler.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.return_value = None

            result = _get_weather_api_key(user_id, mock_db)

            assert result is None

    def test_get_weather_api_key_error(self):
        """Test API key retrieval with error."""
        user_id = "test-user-id"
        mock_db = Mock()

        with patch("app.integrations.simple_plugins.weather_scheduler.get_service_connection_by_user_and_service") as mock_get_conn:
            mock_get_conn.side_effect = Exception("Database error")

            result = _get_weather_api_key(user_id, mock_db)

            assert result is None


class TestExtractWeatherVariables:
    """Tests for _extract_weather_variables function."""

    def test_extract_weather_variables_complete(self):
        """Test extracting all weather variables."""
        weather_data = {
            "main": {
                "temp": 20.5,
                "feels_like": 19.0,
                "temp_min": 18.0,
                "temp_max": 22.0,
                "pressure": 1013,
                "humidity": 65
            },
            "weather": [
                {
                    "main": "Clear",
                    "description": "clear sky"
                }
            ],
            "wind": {
                "speed": 3.5,
                "deg": 180
            },
            "clouds": {
                "all": 10
            },
            "name": "Paris"
        }

        result = _extract_weather_variables(weather_data)

        assert result["weather.temperature"] == 20.5
        assert result["weather.feels_like"] == 19.0
        assert result["weather.temp_min"] == 18.0
        assert result["weather.temp_max"] == 22.0
        assert result["weather.pressure"] == 1013
        assert result["weather.humidity"] == 65
        assert result["weather.condition"] == "Clear"
        assert result["weather.description"] == "clear sky"
        assert result["weather.wind_speed"] == 3.5
        assert result["weather.wind_deg"] == 180
        assert result["weather.clouds"] == 10
        assert result["weather.location"] == "Paris"

    def test_extract_weather_variables_minimal(self):
        """Test extracting weather variables with minimal data."""
        weather_data = {
            "main": {},
            "weather": [],
            "wind": {}
        }

        result = _extract_weather_variables(weather_data)

        assert result["weather.temperature"] is None
        assert result["weather.condition"] is None


class TestCheckTemperatureThreshold:
    """Tests for _check_temperature_threshold function."""

    @pytest.mark.asyncio
    async def test_check_temperature_threshold_above_crossed(self):
        """Test temperature threshold crossed above."""
        area = Mock()
        area.trigger_params = {"threshold": 25.0, "operator": "above"}
        area_id_str = "area123"

        weather_data = {
            "main": {"temp": 26.0}
        }

        # Set previous temperature below threshold
        _last_weather_state[area_id_str] = {"temperature": 24.0}

        result = await _check_temperature_threshold(area, weather_data, area_id_str)

        assert result is True
        assert _last_weather_state[area_id_str]["temperature"] == 26.0

    @pytest.mark.asyncio
    async def test_check_temperature_threshold_below_crossed(self):
        """Test temperature threshold crossed below."""
        area = Mock()
        area.trigger_params = {"threshold": 10.0, "operator": "below"}
        area_id_str = "area456"

        weather_data = {
            "main": {"temp": 9.0}
        }

        # Set previous temperature above threshold
        _last_weather_state[area_id_str] = {"temperature": 11.0}

        result = await _check_temperature_threshold(area, weather_data, area_id_str)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_temperature_threshold_not_crossed(self):
        """Test temperature threshold not crossed."""
        area = Mock()
        area.trigger_params = {"threshold": 25.0, "operator": "above"}
        area_id_str = "area789"

        weather_data = {
            "main": {"temp": 24.5}
        }

        _last_weather_state[area_id_str] = {"temperature": 23.0}

        result = await _check_temperature_threshold(area, weather_data, area_id_str)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_temperature_threshold_first_check(self):
        """Test temperature threshold on first check."""
        area = Mock()
        area.trigger_params = {"threshold": 25.0, "operator": "above"}
        area_id_str = "area_first"

        weather_data = {
            "main": {"temp": 26.0}
        }

        _last_weather_state[area_id_str] = {}

        result = await _check_temperature_threshold(area, weather_data, area_id_str)

        # Should not trigger on first check
        assert result is False

    @pytest.mark.asyncio
    async def test_check_temperature_threshold_no_threshold(self):
        """Test temperature threshold with no threshold configured."""
        area = Mock()
        area.trigger_params = {}
        area_id_str = "area_no_thresh"

        weather_data = {
            "main": {"temp": 26.0}
        }

        result = await _check_temperature_threshold(area, weather_data, area_id_str)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_temperature_threshold_no_temp_data(self):
        """Test temperature threshold with no temperature data."""
        area = Mock()
        area.trigger_params = {"threshold": 25.0, "operator": "above"}
        area_id_str = "area_no_temp"

        weather_data = {
            "main": {}
        }

        result = await _check_temperature_threshold(area, weather_data, area_id_str)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_temperature_threshold_unknown_operator(self):
        """Test temperature threshold with unknown operator."""
        area = Mock()
        area.trigger_params = {"threshold": 25.0, "operator": "invalid"}
        area_id_str = "area_invalid"

        weather_data = {
            "main": {"temp": 26.0}
        }

        _last_weather_state[area_id_str] = {"temperature": 24.0}

        result = await _check_temperature_threshold(area, weather_data, area_id_str)

        assert result is False


class TestCheckWeatherCondition:
    """Tests for _check_weather_condition function."""

    @pytest.mark.asyncio
    async def test_check_weather_condition_match_and_changed(self):
        """Test weather condition matches and has changed."""
        area = Mock()
        area.trigger_params = {"condition": "Rain"}
        area_id_str = "area_rain"

        weather_data = {
            "weather": [{"main": "Rain"}]
        }

        _last_weather_state[area_id_str] = {"condition": "clear"}

        result = await _check_weather_condition(area, weather_data, area_id_str)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_weather_condition_match_not_changed(self):
        """Test weather condition matches but hasn't changed."""
        area = Mock()
        area.trigger_params = {"condition": "Rain"}
        area_id_str = "area_rain2"

        weather_data = {
            "weather": [{"main": "Rain"}]
        }

        _last_weather_state[area_id_str] = {"condition": "rain"}

        result = await _check_weather_condition(area, weather_data, area_id_str)

        # Should not trigger if condition hasn't changed
        assert result is False

    @pytest.mark.asyncio
    async def test_check_weather_condition_no_match(self):
        """Test weather condition doesn't match."""
        area = Mock()
        area.trigger_params = {"condition": "Snow"}
        area_id_str = "area_snow"

        weather_data = {
            "weather": [{"main": "Rain"}]
        }

        _last_weather_state[area_id_str] = {}

        result = await _check_weather_condition(area, weather_data, area_id_str)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_weather_condition_no_condition_param(self):
        """Test weather condition with no condition parameter."""
        area = Mock()
        area.trigger_params = {}
        area_id_str = "area_no_cond"

        weather_data = {
            "weather": [{"main": "Rain"}]
        }

        result = await _check_weather_condition(area, weather_data, area_id_str)

        assert result is False


class TestProcessWeatherTrigger:
    """Tests for _process_weather_trigger function."""

    @pytest.mark.asyncio
    async def test_process_weather_trigger_success(self):
        """Test processing weather trigger successfully."""
        from uuid import uuid4

        mock_db = Mock()
        mock_area = Mock()
        mock_area.id = uuid4()
        mock_area.user_id = uuid4()
        mock_area.name = "Weather Area"
        mock_area.steps = []

        weather_data = {
            "main": {"temp": 20.5},
            "weather": [{"main": "Clear"}]
        }

        now = datetime.now(timezone.utc)

        with patch("app.integrations.simple_plugins.weather_scheduler.create_execution_log") as mock_create_log, \
             patch("app.integrations.simple_plugins.weather_scheduler.execute_area") as mock_execute:

            mock_log = Mock()
            mock_log.status = "Started"
            mock_create_log.return_value = mock_log
            
            mock_execute.return_value = {
                "status": "success",
                "steps_executed": 1,
                "execution_log": []
            }

            mock_db.merge.return_value = mock_area

            await _process_weather_trigger(mock_db, mock_area, weather_data, now)

            mock_create_log.assert_called_once()
            mock_execute.assert_called_once()
            assert mock_log.status == "Success"
            mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_process_weather_trigger_failure(self):
        """Test processing weather trigger with failure."""
        from uuid import uuid4

        mock_db = Mock()
        mock_area = Mock()
        mock_area.id = uuid4()
        mock_area.user_id = uuid4()
        mock_area.name = "Weather Area"

        weather_data = {
            "main": {"temp": 20.5}
        }

        now = datetime.now(timezone.utc)

        with patch("app.integrations.simple_plugins.weather_scheduler.create_execution_log") as mock_create_log, \
             patch("app.integrations.simple_plugins.weather_scheduler.execute_area") as mock_execute:

            mock_log = Mock()
            mock_log.status = "Started"
            mock_create_log.return_value = mock_log
            
            mock_execute.side_effect = Exception("Execution error")
            mock_db.merge.return_value = mock_area

            await _process_weather_trigger(mock_db, mock_area, weather_data, now)

            assert mock_log.status == "Failed"
            mock_db.commit.assert_called()


class TestWeatherSchedulerManagement:
    """Tests for weather scheduler management functions."""

    def test_start_weather_scheduler(self):
        """Test starting weather scheduler."""
        with patch("app.integrations.simple_plugins.weather_scheduler._weather_scheduler_task", None), \
             patch("app.integrations.simple_plugins.weather_scheduler.asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_task = Mock()
            mock_loop.create_task.return_value = mock_task
            mock_get_loop.return_value = mock_loop

            start_weather_scheduler()

            mock_loop.create_task.assert_called_once()

    def test_start_weather_scheduler_already_running(self):
        """Test starting weather scheduler when already running."""
        with patch("app.integrations.simple_plugins.weather_scheduler._weather_scheduler_task", Mock()):
            # Should log warning but not crash
            start_weather_scheduler()

    def test_start_weather_scheduler_no_loop(self):
        """Test starting weather scheduler with no event loop."""
        with patch("app.integrations.simple_plugins.weather_scheduler.asyncio.get_running_loop") as mock_get_loop:
            mock_get_loop.side_effect = RuntimeError("No loop")

            # Should log error but not crash
            start_weather_scheduler()

    def test_stop_weather_scheduler(self):
        """Test stopping weather scheduler."""
        mock_task = Mock()
        with patch("app.integrations.simple_plugins.weather_scheduler._weather_scheduler_task", mock_task):
            stop_weather_scheduler()
            mock_task.cancel.assert_called_once()

    def test_is_weather_scheduler_running_true(self):
        """Test checking if scheduler is running when it is."""
        mock_task = Mock()
        mock_task.done.return_value = False
        with patch("app.integrations.simple_plugins.weather_scheduler._weather_scheduler_task", mock_task):
            assert is_weather_scheduler_running() is True

    def test_is_weather_scheduler_running_false(self):
        """Test checking if scheduler is running when it's not."""
        with patch("app.integrations.simple_plugins.weather_scheduler._weather_scheduler_task", None):
            assert is_weather_scheduler_running() is False

    def test_clear_weather_state(self):
        """Test clearing weather state."""
        # Add some state
        _last_weather_state["test"] = {"temperature": 20.0}
        
        clear_weather_state()
        
        assert len(_last_weather_state) == 0


class TestWeatherSchedulerIntegration:
    """Integration tests for weather scheduler."""

    @pytest.mark.asyncio
    async def test_weather_scheduler_processes_areas(self):
        """Test weather scheduler processes areas correctly."""
        from uuid import uuid4

        with patch("app.db.session.SessionLocal") as mock_session, \
             patch("asyncio.sleep") as mock_sleep, \
             patch("app.integrations.simple_plugins.weather_scheduler._fetch_due_weather_areas") as mock_fetch_areas, \
             patch("app.integrations.simple_plugins.weather_scheduler._get_weather_api_key") as mock_get_key, \
             patch("app.integrations.simple_plugins.weather_scheduler._fetch_weather_data") as mock_fetch_weather, \
             patch("app.integrations.simple_plugins.weather_scheduler._check_temperature_threshold") as mock_check_temp, \
             patch("app.integrations.simple_plugins.weather_scheduler._process_weather_trigger") as mock_process:

            # Setup mocks
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            
            mock_area = Mock()
            mock_area.id = uuid4()
            mock_area.user_id = uuid4()
            mock_area.name = "Test Weather Area"
            mock_area.trigger_action = "temperature_threshold"
            mock_area.trigger_params = {"location": "Paris", "threshold": 25.0}
            
            mock_fetch_areas.return_value = [mock_area]
            mock_get_key.return_value = "test_api_key"
            mock_fetch_weather.return_value = {"main": {"temp": 26.0}}
            mock_check_temp.return_value = True

            mock_db = Mock()
            mock_db.__enter__ = Mock(return_value=mock_db)
            mock_db.__exit__ = Mock(return_value=None)
            mock_session.return_value = mock_db

            # Run scheduler
            await weather_scheduler_task()

            # Should have processed the trigger
            mock_process.assert_called()

    def test_fetch_weather_with_lat_lon(self):
        """Test fetching weather data with lat/lon coordinates."""
        with patch("app.integrations.simple_plugins.weather_scheduler.httpx.Client") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "main": {"temp": 20.5},
                "name": "Location"
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = _fetch_weather_data("test_key", lat=48.8566, lon=2.3522)

            assert result is not None
            assert result["main"]["temp"] == 20.5


