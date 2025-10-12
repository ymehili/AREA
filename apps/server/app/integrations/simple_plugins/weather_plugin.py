"""Weather plugin for AREA - Implements weather data retrieval and condition monitoring.

This plugin integrates with OpenWeatherMap API to provide:
- Current weather data for any location
- 5-day weather forecasts
- Temperature threshold triggers
- Weather condition change triggers

All weather data is fetched using a shared API key (no per-user authentication required).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict
import httpx

from app.core.config import settings
from app.integrations.simple_plugins.exceptions import (
    WeatherAPIError,
    WeatherConfigError,
)

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")

# OpenWeatherMap API base URL
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


def _get_api_key() -> str:
    """Get OpenWeatherMap API key from settings.
    
    Returns:
        API key string
        
    Raises:
        WeatherConfigError: If API key is not configured
    """
    api_key = getattr(settings, "openweathermap_api_key", None)
    if not api_key:
        raise WeatherConfigError(
            "OpenWeatherMap API key not configured. "
            "Please set OPENWEATHERMAP_API_KEY in your environment variables."
        )
    return api_key


def _make_weather_request(endpoint: str, params: dict) -> dict:
    """Make a request to OpenWeatherMap API.
    
    Args:
        endpoint: API endpoint (e.g., "weather", "forecast")
        params: Query parameters (must include location)
        
    Returns:
        JSON response as dictionary
        
    Raises:
        WeatherAPIError: If API request fails
    """
    try:
        api_key = _get_api_key()
        
        # Add API key to params
        params["appid"] = api_key
        
        # Default to metric units if not specified
        if "units" not in params:
            params["units"] = "metric"
        
        url = f"{OPENWEATHER_BASE_URL}/{endpoint}"
        
        logger.debug(
            f"Making Weather API request",
            extra={
                "endpoint": endpoint,
                "params": {k: v for k, v in params.items() if k != "appid"},
            }
        )
        
        # Make synchronous HTTP request
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        
        return response.json()
        
    except httpx.HTTPStatusError as e:
        error_msg = f"Weather API HTTP error: {e.response.status_code}"
        try:
            error_data = e.response.json()
            error_msg += f" - {error_data.get('message', '')}"
        except Exception:
            pass
            
        logger.error(
            "Weather API request failed",
            extra={
                "endpoint": endpoint,
                "status_code": e.response.status_code,
                "error": error_msg,
            },
            exc_info=True
        )
        raise WeatherAPIError(error_msg) from e
        
    except httpx.RequestError as e:
        error_msg = f"Weather API request error: {str(e)}"
        logger.error(
            "Weather API request failed",
            extra={
                "endpoint": endpoint,
                "error": error_msg,
            },
            exc_info=True
        )
        raise WeatherAPIError(error_msg) from e


def get_current_weather_handler(area: Area, params: dict, event: dict) -> None:
    """Fetch current weather data for a specified location.
    
    This action retrieves real-time weather information including:
    - Temperature, feels like temperature
    - Weather condition (rain, snow, clear, etc.)
    - Humidity, pressure
    - Wind speed and direction
    - Cloudiness
    
    Args:
        area: The Area being executed
        params: Action parameters:
            - location (str): City name (e.g., "London", "New York,US") OR
            - lat (float) & lon (float): GPS coordinates
            - units (str, optional): "metric" (default), "imperial", or "standard"
        event: Event data from trigger
        
    Raises:
        ValueError: If location parameters are invalid
        WeatherAPIError: If API request fails
        WeatherConfigError: If API key is not configured
        
    Example params:
        {"location": "Paris,FR", "units": "metric"}
        {"lat": 48.8566, "lon": 2.3522, "units": "metric"}
    """
    try:
        # Extract location parameters
        location = params.get("location")
        lat = params.get("lat")
        lon = params.get("lon")
        units = params.get("units", "metric")
        
        logger.info(
            "Starting Weather get_current_weather action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "location": location,
                "lat": lat,
                "lon": lon,
                "units": units,
            }
        )
        
        # Build request parameters
        request_params = {"units": units}
        
        if lat is not None and lon is not None:
            # Use coordinates
            request_params["lat"] = lat
            request_params["lon"] = lon
            location_str = f"lat={lat}, lon={lon}"
        elif location:
            # Use city name
            request_params["q"] = location
            location_str = location
        else:
            raise ValueError(
                "Either 'location' (city name) or both 'lat' and 'lon' (coordinates) must be provided"
            )
        
        # Make API request
        weather_data = _make_weather_request("weather", request_params)
        
        # Extract key information for logging
        temp = weather_data.get("main", {}).get("temp")
        feels_like = weather_data.get("main", {}).get("feels_like")
        condition = weather_data.get("weather", [{}])[0].get("main", "Unknown")
        description = weather_data.get("weather", [{}])[0].get("description", "")
        humidity = weather_data.get("main", {}).get("humidity")
        wind_speed = weather_data.get("wind", {}).get("speed")
        
        logger.info(
            "Current weather data retrieved successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "location": location_str,
                "temperature": temp,
                "feels_like": feels_like,
                "condition": condition,
                "description": description,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "units": units,
                "weather_data": weather_data,
            }
        )
        
        # Store weather data in event for potential chaining with other actions
        event["weather.temperature"] = temp
        event["weather.feels_like"] = feels_like
        event["weather.condition"] = condition
        event["weather.description"] = description
        event["weather.humidity"] = humidity
        event["weather.wind_speed"] = wind_speed
        event["weather.location"] = location_str
        event["weather.units"] = units
        
        # Store full weather data for display in execution logs
        event["weather_data"] = {
            "temperature": temp,
            "feels_like": feels_like,
            "condition": condition,
            "description": description,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "location": location_str,
            "units": units,
            "pressure": weather_data.get("main", {}).get("pressure"),
            "clouds": weather_data.get("clouds", {}).get("all"),
        }
        
    except ValueError as e:
        logger.error(
            "Invalid parameters for get_current_weather",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            }
        )
        raise
    except Exception as e:
        logger.error(
            "Error fetching current weather",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


def get_forecast_handler(area: Area, params: dict, event: dict) -> None:
    """Retrieve 5-day weather forecast for a location.
    
    This action fetches weather forecast data with 3-hour intervals for the next 5 days.
    Each forecast entry includes temperature, weather condition, wind, and more.
    
    Args:
        area: The Area being executed
        params: Action parameters:
            - location (str): City name (e.g., "London", "Tokyo,JP") OR
            - lat (float) & lon (float): GPS coordinates
            - units (str, optional): "metric" (default), "imperial", or "standard"
            - cnt (int, optional): Number of forecast entries to retrieve (max 40)
        event: Event data from trigger
        
    Raises:
        ValueError: If location parameters are invalid
        WeatherAPIError: If API request fails
        WeatherConfigError: If API key is not configured
        
    Example params:
        {"location": "Berlin,DE", "units": "metric", "cnt": 8}
        {"lat": 52.52, "lon": 13.405, "units": "metric"}
    """
    try:
        # Extract location parameters
        location = params.get("location")
        lat = params.get("lat")
        lon = params.get("lon")
        units = params.get("units", "metric")
        cnt = params.get("cnt")  # Optional: number of forecast entries
        
        logger.info(
            "Starting Weather get_forecast action",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "location": location,
                "lat": lat,
                "lon": lon,
                "units": units,
                "cnt": cnt,
            }
        )
        
        # Build request parameters
        request_params = {"units": units}
        
        if lat is not None and lon is not None:
            # Use coordinates
            request_params["lat"] = lat
            request_params["lon"] = lon
            location_str = f"lat={lat}, lon={lon}"
        elif location:
            # Use city name
            request_params["q"] = location
            location_str = location
        else:
            raise ValueError(
                "Either 'location' (city name) or both 'lat' and 'lon' (coordinates) must be provided"
            )
        
        # Add optional count parameter
        if cnt:
            request_params["cnt"] = cnt
        
        # Make API request
        forecast_data = _make_weather_request("forecast", request_params)
        
        # Extract summary information
        forecast_list = forecast_data.get("list", [])
        num_forecasts = len(forecast_list)
        
        # Get first forecast for immediate preview
        if forecast_list:
            first_forecast = forecast_list[0]
            first_temp = first_forecast.get("main", {}).get("temp")
            first_condition = first_forecast.get("weather", [{}])[0].get("main", "Unknown")
            first_dt = first_forecast.get("dt_txt", "")
        else:
            first_temp = None
            first_condition = None
            first_dt = None
        
        logger.info(
            "Weather forecast retrieved successfully",
            extra={
                "area_id": str(area.id),
                "area_name": area.name,
                "user_id": str(area.user_id),
                "location": location_str,
                "num_forecasts": num_forecasts,
                "first_forecast_time": first_dt,
                "first_forecast_temp": first_temp,
                "first_forecast_condition": first_condition,
                "units": units,
            }
        )
        
        # Store forecast data in event for potential use in subsequent actions
        event["weather.forecast_count"] = num_forecasts
        event["weather.location"] = location_str
        if first_temp is not None:
            event["weather.next_temperature"] = first_temp
            event["weather.next_condition"] = first_condition
            event["weather.next_forecast_time"] = first_dt
        
        # Store full forecast data (useful for advanced workflows)
        event["weather.forecast_data"] = forecast_data
        
        # Store weather data for display in execution logs (similar to current weather)
        # This will be picked up by step_executor.py and included in the step log
        event["weather_data"] = {
            "type": "forecast",
            "location": location_str,
            "units": units,
            "forecast_count": num_forecasts,
            "forecast_data": forecast_data,
        }
        
    except ValueError as e:
        logger.error(
            "Invalid parameters for get_forecast",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            }
        )
        raise
    except Exception as e:
        logger.error(
            "Error fetching weather forecast",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True
        )
        raise


__all__ = [
    "get_current_weather_handler",
    "get_forecast_handler",
]
