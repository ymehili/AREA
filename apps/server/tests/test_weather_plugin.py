"""Tests for Weather plugin handlers - Updated for user API keys."""

from __future__ import annotations

from unittest.mock import Mock, patch, MagicMock
import uuid

import pytest
import httpx

from app.integrations.simple_plugins.weather_plugin import (
    _get_weather_api_key,
    get_current_weather_handler,
    get_forecast_handler,
)
from app.integrations.simple_plugins.exceptions import (
    WeatherAPIError,
    WeatherConfigError,
)
from app.models.service_connection import ServiceConnection
from app.models.area import Area


class TestWeatherPluginWithUserAPIKey:
    """Test Weather plugin with user-provided API keys."""

    @pytest.fixture
    def area(self):
        """Create a mock area object for testing."""
        area = Area()
        area.id = uuid.uuid4()
        area.name = "Test Weather Area"
        area.user_id = uuid.uuid4()
        return area

    @pytest.fixture
    def mock_service_connection(self):
        """Create a mock service connection."""
        connection = ServiceConnection()
        connection.encrypted_access_token = "encrypted_test_key"
        return connection

    def test_get_weather_api_key_success(self, area, mock_service_connection):
        """Test successful retrieval of API key from service connection."""
        mock_db = MagicMock()
        
        with patch("app.integrations.simple_plugins.weather_plugin.get_service_connection_by_user_and_service", return_value=mock_service_connection):
            with patch("app.integrations.simple_plugins.weather_plugin.decrypt_token", return_value="decrypted_api_key"):
                api_key = _get_weather_api_key(area, mock_db)
                assert api_key == "decrypted_api_key"

    def test_get_weather_api_key_no_connection(self, area):
        """Test that missing service connection raises WeatherConfigError."""
        mock_db = MagicMock()
        
        with patch("app.integrations.simple_plugins.weather_plugin.get_service_connection_by_user_and_service", return_value=None):
            with pytest.raises(WeatherConfigError, match="Weather service connection not found"):
                _get_weather_api_key(area, mock_db)

    def test_current_weather_handler_success(self, area):
        """Test successful current weather fetch."""
        params = {
            "location": "Paris,FR",
            "units": "metric"
        }
        event = {}
        
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
        
        mock_db = MagicMock()
        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"
        
        with patch("app.integrations.simple_plugins.weather_plugin.SessionLocal", return_value=mock_db):
            with patch("app.integrations.simple_plugins.weather_plugin.get_service_connection_by_user_and_service", return_value=mock_connection):
                with patch("app.integrations.simple_plugins.weather_plugin.decrypt_token", return_value="test_api_key"):
                    with patch("httpx.get") as mock_get:
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = mock_weather_data
                        mock_response.raise_for_status.return_value = None
                        mock_get.return_value = mock_response
                        
                        get_current_weather_handler(area, params, event)
                        
                        # Verify event populated correctly
                        assert event["weather.temperature"] == 18.5
                        assert event["weather.condition"] == "Clouds"
                        assert event["weather.location"] == "Paris,FR"
                        assert "weather_data" in event
                        
                        # Verify DB session was closed
                        mock_db.close.assert_called_once()

    def test_current_weather_handler_no_api_key(self, area):
        """Test current weather fails without API key."""
        params = {"location": "London"}
        event = {}
        
        mock_db = MagicMock()
        
        with patch("app.integrations.simple_plugins.weather_plugin.SessionLocal", return_value=mock_db):
            with patch("app.integrations.simple_plugins.weather_plugin.get_service_connection_by_user_and_service", return_value=None):
                with pytest.raises(WeatherConfigError, match="Weather service connection not found"):
                    get_current_weather_handler(area, params, event)
                
                # DB session should still be closed even on error
                mock_db.close.assert_called_once()

    def test_forecast_handler_success(self, area):
        """Test successful forecast retrieval."""
        params = {
            "location": "Berlin,DE",
            "units": "metric"
        }
        event = {}
        
        mock_forecast_data = {
            "list": [
                {
                    "dt": 1609459200,
                    "dt_txt": "2021-01-01 00:00:00",
                    "main": {"temp": 15.2, "humidity": 70},
                    "weather": [{"main": "Clear", "description": "clear sky"}]
                }
            ]
        }
        
        mock_db = MagicMock()
        mock_connection = ServiceConnection()
        mock_connection.encrypted_access_token = "encrypted_test_key"
        
        with patch("app.integrations.simple_plugins.weather_plugin.SessionLocal", return_value=mock_db):
            with patch("app.integrations.simple_plugins.weather_plugin.get_service_connection_by_user_and_service", return_value=mock_connection):
                with patch("app.integrations.simple_plugins.weather_plugin.decrypt_token", return_value="test_api_key"):
                    with patch("httpx.get") as mock_get:
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = mock_forecast_data
                        mock_response.raise_for_status.return_value = None
                        mock_get.return_value = mock_response
                        
                        get_forecast_handler(area, params, event)
                        
                        # Verify event populated correctly
                        assert event["weather.forecast_count"] == 1
                        assert event["weather.location"] == "Berlin,DE"
                        assert "weather_data" in event
                        assert event["weather_data"]["type"] == "forecast"
                        
                        # Verify DB session was closed
                        mock_db.close.assert_called_once()

    def test_missing_location_raises_error(self, area):
        """Test that missing location raises ValueError."""
        params = {"units": "metric"}  # No location
        event = {}
        
        with pytest.raises(ValueError, match="Either 'location'.*or both 'lat' and 'lon'.*must be provided"):
            get_current_weather_handler(area, params, event)
