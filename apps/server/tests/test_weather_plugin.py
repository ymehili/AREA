"""Tests for Weather plugin handlers."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import httpx

from app.integrations.simple_plugins.weather_plugin import (
    _get_api_key,
    _make_weather_request,
    get_current_weather_handler,
    get_forecast_handler,
)
from app.integrations.simple_plugins.exceptions import (
    WeatherAPIError,
    WeatherConfigError,
)


class TestWeatherPlugin:
    """Test Weather plugin functionality."""

    def test_get_api_key_success(self, monkeypatch):
        """Test successful retrieval of API key from settings."""
        from app.core import config
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key_12345")
        
        api_key = _get_api_key()
        assert api_key == "test_api_key_12345"

    def test_get_api_key_missing_raises_config_error(self, monkeypatch):
        """Test that missing OPENWEATHERMAP_API_KEY raises WeatherConfigError."""
        from app.core import config
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", None)
        
        with pytest.raises(WeatherConfigError, match="OpenWeatherMap API key not configured"):
            _get_api_key()

    def test_make_weather_request_success(self, monkeypatch):
        """Test successful weather API request."""
        from app.core import config
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        # Mock httpx.get response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {"temp": 20.5, "humidity": 65},
            "weather": [{"main": "Clear", "description": "clear sky"}]
        }
        mock_response.raise_for_status.return_value = None
        
        with patch("httpx.get", return_value=mock_response) as mock_get:
            result = _make_weather_request("weather", {"q": "London"})
            
            assert result["main"]["temp"] == 20.5
            assert result["weather"][0]["main"] == "Clear"
            
            # Verify API call was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "weather" in call_args[0][0]
            assert call_args[1]["params"]["appid"] == "test_api_key"
            assert call_args[1]["params"]["q"] == "London"
            assert call_args[1]["params"]["units"] == "metric"

    def test_make_weather_request_http_error(self, monkeypatch):
        """Test weather API HTTP errors are converted to WeatherAPIError."""
        from app.core import config
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        # Mock httpx.HTTPStatusError
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "city not found"}
        
        http_error = httpx.HTTPStatusError(
            "404 error",
            request=Mock(),
            response=mock_response
        )
        
        with patch("httpx.get") as mock_get:
            mock_get.return_value.raise_for_status.side_effect = http_error
            
            with pytest.raises(WeatherAPIError, match="Weather API HTTP error: 404"):
                _make_weather_request("weather", {"q": "InvalidCity"})

    def test_make_weather_request_connection_error(self, monkeypatch):
        """Test weather API connection errors are converted to WeatherAPIError."""
        from app.core import config
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        # Mock httpx.RequestError (network error)
        request_error = httpx.RequestError("Connection timeout")
        
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = request_error
            
            with pytest.raises(WeatherAPIError, match="Weather API request error"):
                _make_weather_request("weather", {"q": "London"})

    def test_get_current_weather_with_city_name(self, db_session, monkeypatch):
        """Test fetching weather by city name."""
        from app.core import config
        
        # Setup
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Weather Area"
        
        params = {
            "location": "Paris,FR",
            "units": "metric"
        }
        event = {}
        
        # Mock API response
        mock_weather_data = {
            "main": {
                "temp": 18.5,
                "feels_like": 17.2,
                "humidity": 72,
                "pressure": 1013
            },
            "weather": [
                {"main": "Clouds", "description": "scattered clouds"}
            ],
            "wind": {"speed": 3.5},
            "clouds": {"all": 40}
        }
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_weather_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Execute
            get_current_weather_handler(area, params, event)
            
            # Verify event was populated correctly
            assert event["weather.temperature"] == 18.5
            assert event["weather.feels_like"] == 17.2
            assert event["weather.condition"] == "Clouds"
            assert event["weather.description"] == "scattered clouds"
            assert event["weather.humidity"] == 72
            assert event["weather.wind_speed"] == 3.5
            assert event["weather.location"] == "Paris,FR"
            assert event["weather.units"] == "metric"
            
            # Verify weather_data structure
            assert "weather_data" in event
            assert event["weather_data"]["temperature"] == 18.5
            assert event["weather_data"]["pressure"] == 1013
            assert event["weather_data"]["clouds"] == 40

    def test_get_current_weather_with_coordinates(self, db_session, monkeypatch):
        """Test fetching weather by lat/lon."""
        from app.core import config
        
        # Setup
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Weather Area"
        
        params = {
            "lat": 48.8566,
            "lon": 2.3522,
            "units": "imperial"
        }
        event = {}
        
        # Mock API response
        mock_weather_data = {
            "main": {
                "temp": 65.3,
                "feels_like": 63.5,
                "humidity": 68,
                "pressure": 1015
            },
            "weather": [
                {"main": "Rain", "description": "light rain"}
            ],
            "wind": {"speed": 5.2},
            "clouds": {"all": 80}
        }
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_weather_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Execute
            get_current_weather_handler(area, params, event)
            
            # Verify event was populated correctly
            assert event["weather.temperature"] == 65.3
            assert event["weather.feels_like"] == 63.5
            assert event["weather.condition"] == "Rain"
            assert event["weather.description"] == "light rain"
            assert event["weather.humidity"] == 68
            assert event["weather.wind_speed"] == 5.2
            assert event["weather.location"] == "lat=48.8566, lon=2.3522"
            assert event["weather.units"] == "imperial"
            
            # Verify API was called with coordinates
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["lat"] == 48.8566
            assert call_args[1]["params"]["lon"] == 2.3522
            assert call_args[1]["params"]["units"] == "imperial"

    def test_get_current_weather_missing_location_raises_value_error(self, db_session):
        """Test that missing both location and lat/lon raises ValueError."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Weather Area"
        
        params = {"units": "metric"}  # Missing location AND lat/lon
        event = {}
        
        with pytest.raises(ValueError, match="Either 'location'.*or both 'lat' and 'lon'.*must be provided"):
            get_current_weather_handler(area, params, event)

    def test_get_current_weather_partial_coordinates_raises_value_error(self, db_session):
        """Test that providing only lat or only lon raises ValueError."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Weather Area"
        
        # Test with only lat
        params_lat_only = {"lat": 48.8566, "units": "metric"}
        event = {}
        
        with pytest.raises(ValueError, match="Either 'location'.*or both 'lat' and 'lon'.*must be provided"):
            get_current_weather_handler(area, params_lat_only, event)
        
        # Test with only lon
        params_lon_only = {"lon": 2.3522, "units": "metric"}
        event = {}
        
        with pytest.raises(ValueError, match="Either 'location'.*or both 'lat' and 'lon'.*must be provided"):
            get_current_weather_handler(area, params_lon_only, event)

    def test_get_current_weather_api_error_propagates(self, db_session, monkeypatch):
        """Test that WeatherAPIError is propagated when API fails."""
        from app.core import config
        
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Weather Area"
        
        params = {"location": "London", "units": "metric"}
        event = {}
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid API key"}
        
        http_error = httpx.HTTPStatusError(
            "401 error",
            request=Mock(),
            response=mock_response
        )
        
        with patch("httpx.get") as mock_get:
            mock_get.return_value.raise_for_status.side_effect = http_error
            
            with pytest.raises(WeatherAPIError, match="Weather API HTTP error: 401"):
                get_current_weather_handler(area, params, event)

    def test_get_current_weather_default_units(self, db_session, monkeypatch):
        """Test that default units are metric when not specified."""
        from app.core import config
        
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Weather Area"
        
        params = {"location": "Tokyo,JP"}  # No units specified
        event = {}
        
        mock_weather_data = {
            "main": {"temp": 25.0, "feels_like": 24.0, "humidity": 60, "pressure": 1010},
            "weather": [{"main": "Clear", "description": "clear sky"}],
            "wind": {"speed": 2.5},
            "clouds": {"all": 0}
        }
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_weather_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            get_current_weather_handler(area, params, event)
            
            # Verify units default to metric
            assert event["weather.units"] == "metric"
            
            # Verify API call used metric
            call_args = mock_get.call_args
            assert call_args[1]["params"]["units"] == "metric"

    def test_get_forecast_with_city_name(self, db_session, monkeypatch):
        """Test forecast retrieval by city name."""
        from app.core import config
        
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Forecast Area"
        
        params = {
            "location": "Berlin,DE",
            "units": "metric",
            "cnt": 8
        }
        event = {}
        
        # Mock forecast response
        mock_forecast_data = {
            "list": [
                {
                    "dt": 1609459200,
                    "dt_txt": "2021-01-01 00:00:00",
                    "main": {"temp": 15.2, "humidity": 70},
                    "weather": [{"main": "Clear", "description": "clear sky"}]
                },
                {
                    "dt": 1609470000,
                    "dt_txt": "2021-01-01 03:00:00",
                    "main": {"temp": 14.8, "humidity": 72},
                    "weather": [{"main": "Clouds", "description": "few clouds"}]
                }
            ]
        }
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_forecast_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Execute
            get_forecast_handler(area, params, event)
            
            # Verify event was populated
            assert event["weather.forecast_count"] == 2
            assert event["weather.location"] == "Berlin,DE"
            assert event["weather.next_temperature"] == 15.2
            assert event["weather.next_condition"] == "Clear"
            assert event["weather.next_forecast_time"] == "2021-01-01 00:00:00"
            assert "weather.forecast_data" in event
            
            # Verify weather_data for logs
            assert event["weather_data"]["type"] == "forecast"
            assert event["weather_data"]["forecast_count"] == 2
            
            # Verify API call
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "forecast" in call_args[0][0]
            assert call_args[1]["params"]["q"] == "Berlin,DE"
            assert call_args[1]["params"]["cnt"] == 8

    def test_get_forecast_with_coordinates(self, db_session, monkeypatch):
        """Test forecast retrieval by coordinates."""
        from app.core import config
        
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Forecast Area"
        
        params = {
            "lat": 52.52,
            "lon": 13.405,
            "units": "imperial"
        }
        event = {}
        
        # Mock forecast response
        mock_forecast_data = {
            "list": [
                {
                    "dt": 1609459200,
                    "dt_txt": "2021-01-01 00:00:00",
                    "main": {"temp": 59.0, "humidity": 68},
                    "weather": [{"main": "Rain", "description": "light rain"}]
                }
            ]
        }
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_forecast_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Execute
            get_forecast_handler(area, params, event)
            
            # Verify event
            assert event["weather.forecast_count"] == 1
            assert event["weather.location"] == "lat=52.52, lon=13.405"
            assert event["weather.next_temperature"] == 59.0
            
            # Verify API call with coordinates
            call_args = mock_get.call_args
            assert call_args[1]["params"]["lat"] == 52.52
            assert call_args[1]["params"]["lon"] == 13.405

    def test_get_forecast_missing_location_raises_value_error(self, db_session):
        """Test that missing location parameters raises ValueError."""
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Forecast Area"
        
        params = {"units": "metric"}  # Missing location
        event = {}
        
        with pytest.raises(ValueError, match="Either 'location'.*or both 'lat' and 'lon'.*must be provided"):
            get_forecast_handler(area, params, event)

    def test_get_forecast_empty_list(self, db_session, monkeypatch):
        """Test forecast handling when API returns empty list."""
        from app.core import config
        
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Forecast Area"
        
        params = {"location": "London"}
        event = {}
        
        # Mock empty forecast response
        mock_forecast_data = {"list": []}
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_forecast_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Execute
            get_forecast_handler(area, params, event)
            
            # Verify event handles empty list
            assert event["weather.forecast_count"] == 0
            assert "weather.next_temperature" not in event
            assert "weather.next_condition" not in event

    def test_get_forecast_api_error_propagates(self, db_session, monkeypatch):
        """Test that WeatherAPIError is propagated on forecast failure."""
        from app.core import config
        
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Forecast Area"
        
        params = {"location": "InvalidCity"}
        event = {}
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "city not found"}
        
        http_error = httpx.HTTPStatusError(
            "404 error",
            request=Mock(),
            response=mock_response
        )
        
        with patch("httpx.get") as mock_get:
            mock_get.return_value.raise_for_status.side_effect = http_error
            
            with pytest.raises(WeatherAPIError, match="Weather API HTTP error: 404"):
                get_forecast_handler(area, params, event)

    def test_get_forecast_without_cnt_parameter(self, db_session, monkeypatch):
        """Test forecast without optional cnt parameter."""
        from app.core import config
        
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Forecast Area"
        
        params = {"location": "Madrid,ES"}  # No cnt parameter
        event = {}
        
        mock_forecast_data = {
            "list": [
                {"dt": 1609459200, "dt_txt": "2021-01-01 00:00:00", 
                 "main": {"temp": 12.0}, "weather": [{"main": "Clear"}]}
            ]
        }
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_forecast_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            get_forecast_handler(area, params, event)
            
            # Verify cnt was not included in API call
            call_args = mock_get.call_args
            assert "cnt" not in call_args[1]["params"]

    def test_make_weather_request_adds_default_metric_units(self, monkeypatch):
        """Test that _make_weather_request adds metric units by default."""
        from app.core import config
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        
        with patch("httpx.get", return_value=mock_response) as mock_get:
            _make_weather_request("weather", {"q": "London"})
            
            call_args = mock_get.call_args
            assert call_args[1]["params"]["units"] == "metric"

    def test_make_weather_request_respects_custom_units(self, monkeypatch):
        """Test that _make_weather_request respects custom units parameter."""
        from app.core import config
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        
        with patch("httpx.get", return_value=mock_response) as mock_get:
            _make_weather_request("weather", {"q": "London", "units": "imperial"})
            
            call_args = mock_get.call_args
            assert call_args[1]["params"]["units"] == "imperial"

    def test_make_weather_request_http_error_without_json(self, monkeypatch):
        """Test HTTP error handling when response has no JSON body."""
        from app.core import config
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        # Mock response that raises exception on .json()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("No JSON")
        
        http_error = httpx.HTTPStatusError(
            "500 error",
            request=Mock(),
            response=mock_response
        )
        
        with patch("httpx.get") as mock_get:
            mock_get.return_value.raise_for_status.side_effect = http_error
            
            with pytest.raises(WeatherAPIError, match="Weather API HTTP error: 500"):
                _make_weather_request("weather", {"q": "London"})

    def test_get_current_weather_with_missing_optional_fields(self, db_session, monkeypatch):
        """Test current weather handling when API response has missing optional fields."""
        from app.core import config
        
        area = Mock()
        area.id = "test-area-id"
        area.user_id = "test-user-id"
        area.name = "Test Weather Area"
        
        params = {"location": "London"}
        event = {}
        
        # Mock incomplete weather data - weather array must have at least one element
        # but can have missing fields within it
        mock_weather_data = {
            "main": {"temp": 20.0},  # Missing feels_like, humidity, pressure
            "weather": [{}],  # Empty weather object (no main or description)
            "wind": {},  # Missing speed
            "clouds": {}  # Missing all
        }
        
        monkeypatch.setattr(config.settings, "openweathermap_api_key", "test_api_key")
        
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_weather_data
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Should not raise an error
            get_current_weather_handler(area, params, event)
            
            # Verify it handles missing fields gracefully
            assert event["weather.temperature"] == 20.0
            assert event["weather.feels_like"] is None
            assert event["weather.condition"] == "Unknown"
            assert event["weather.description"] == ""
            assert event["weather.humidity"] is None
            assert event["weather.wind_speed"] is None
