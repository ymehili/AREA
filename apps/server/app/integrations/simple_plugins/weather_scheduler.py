"""Weather polling scheduler for temperature and condition trigger-based automation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

import httpx

from app.core.encryption import decrypt_token
from app.models.area import Area
from app.schemas.execution_log import ExecutionLogCreate
from app.services.execution_logs import create_execution_log
from app.services.service_connections import get_service_connection_by_user_and_service
from app.services.step_executor import execute_area

logger = logging.getLogger("area")

# In-memory storage for last checked values per AREA
_last_weather_state: Dict[str, dict] = {}
_weather_scheduler_task: asyncio.Task | None = None

# OpenWeatherMap API base URL
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


def _get_weather_api_key(user_id, db: Session) -> str | None:
    """Get decrypted OpenWeatherMap API key for a user.
    
    Args:
        user_id: User UUID
        db: Database session
        
    Returns:
        Decrypted API key or None if not found
    """
    try:
        connection = get_service_connection_by_user_and_service(db, user_id, "weather")
        if not connection:
            return None
        return decrypt_token(connection.encrypted_access_token)
    except Exception as e:
        logger.error(f"Failed to get weather API key: {e}", exc_info=True)
        return None


def _fetch_weather_data(api_key: str, location: str = None, lat: float = None, lon: float = None) -> dict | None:
    """Fetch current weather data from OpenWeatherMap API.
    
    Args:
        api_key: OpenWeatherMap API key
        location: City name (e.g., "London,UK")
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        Weather data dictionary or None on error
    """
    try:
        params = {
            "appid": api_key,
            "units": "metric"
        }
        
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        elif location:
            params["q"] = location
        else:
            logger.error("Either location or lat/lon must be provided")
            return None
        
        with httpx.Client() as client:
            response = client.get(
                f"{OPENWEATHER_BASE_URL}/weather",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch weather data: {e}", exc_info=True)
        return None


def _extract_weather_variables(weather_data: dict) -> dict:
    """Extract weather variables for use in workflows.
    
    Args:
        weather_data: Raw weather data from API
        
    Returns:
        Dictionary of weather variables
    """
    main = weather_data.get("main", {})
    weather_list = weather_data.get("weather", [{}])
    weather_item = weather_list[0] if weather_list else {}
    wind = weather_data.get("wind", {})
    
    return {
        "weather.temperature": main.get("temp"),
        "weather.feels_like": main.get("feels_like"),
        "weather.temp_min": main.get("temp_min"),
        "weather.temp_max": main.get("temp_max"),
        "weather.pressure": main.get("pressure"),
        "weather.humidity": main.get("humidity"),
        "weather.condition": weather_item.get("main"),
        "weather.description": weather_item.get("description"),
        "weather.wind_speed": wind.get("speed"),
        "weather.wind_deg": wind.get("deg"),
        "weather.clouds": weather_data.get("clouds", {}).get("all"),
        "weather.location": weather_data.get("name"),
    }


def _fetch_due_weather_areas(db: Session) -> list[Area]:
    """Fetch all enabled areas with weather triggers.
    
    Args:
        db: Database session
        
    Returns:
        List of Area objects
    """
    return (
        db.query(Area)
        .filter(
            Area.enabled == True,  # noqa: E712
            Area.trigger_service == "weather",
        )
        .all()
    )


async def weather_scheduler_task() -> None:
    """Background task that polls weather data and checks for trigger conditions."""
    from app.db.session import SessionLocal

    logger.info("Starting Weather polling scheduler task")

    while True:
        try:
            # Poll every 5 minutes (weather doesn't change that frequently)
            await asyncio.sleep(300)

            now = datetime.now(timezone.utc)

            # Fetch all enabled weather areas using a scoped session
            with SessionLocal() as db:
                areas = await asyncio.to_thread(_fetch_due_weather_areas, db)

                logger.info(
                    "Weather scheduler tick",
                    extra={
                        "utc_now": now.isoformat(),
                        "areas_count": len(areas),
                    },
                )

            # Process each area with its own scoped session
            for area in areas:
                area_id_str = str(area.id)

                # Initialize last state for this area if needed
                if area_id_str not in _last_weather_state:
                    _last_weather_state[area_id_str] = {}

                try:
                    # Use scoped session for this area's processing
                    with SessionLocal() as db:
                        # Get weather API key for user
                        api_key = await asyncio.to_thread(_get_weather_api_key, area.user_id, db)
                        if not api_key:
                            logger.warning(
                                f"Weather API key not configured for area {area_id_str}, skipping"
                            )
                            continue

                        # Get location from trigger params
                        params = area.trigger_params or {}
                        location = params.get("location")
                        lat = params.get("lat")
                        lon = params.get("lon")
                        
                        if not location and (lat is None or lon is None):
                            logger.warning(
                                f"No location configured for weather area {area_id_str}, skipping"
                            )
                            continue

                        # Fetch current weather data
                        weather_data = await asyncio.to_thread(
                            _fetch_weather_data, api_key, location, lat, lon
                        )
                        
                        if not weather_data:
                            logger.warning(
                                f"Failed to fetch weather data for area {area_id_str}"
                            )
                            continue

                        # Check if trigger condition is met based on trigger action
                        should_trigger = False
                        
                        if area.trigger_action == "temperature_threshold":
                            should_trigger = await _check_temperature_threshold(
                                area, weather_data, area_id_str
                            )
                        elif area.trigger_action == "weather_condition":
                            should_trigger = await _check_weather_condition(
                                area, weather_data, area_id_str
                            )

                        if should_trigger:
                            logger.info(
                                f"Weather trigger condition met for area {area_id_str}",
                                extra={
                                    "area_id": area_id_str,
                                    "trigger_action": area.trigger_action,
                                }
                            )
                            await _process_weather_trigger(db, area, weather_data, now)

                except Exception as e:
                    logger.error(
                        "Error processing weather area",
                        extra={
                            "area_id": area_id_str,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            logger.info("Weather scheduler task cancelled, shutting down gracefully")
            break

        except Exception as e:
            logger.error("Weather scheduler task error", extra={"error": str(e)}, exc_info=True)
            await asyncio.sleep(60)  # Back off on error

    logger.info("Weather scheduler task stopped")


async def _check_temperature_threshold(area: Area, weather_data: dict, area_id_str: str) -> bool:
    """Check if temperature threshold condition is met.
    
    Args:
        area: Area with temperature_threshold trigger
        weather_data: Current weather data
        area_id_str: Area ID as string
        
    Returns:
        True if threshold is crossed
    """
    params = area.trigger_params or {}
    threshold = params.get("threshold")
    operator = params.get("operator", "above")  # "above" or "below"
    
    if threshold is None:
        logger.warning(f"No threshold configured for area {area_id_str}")
        return False
    
    current_temp = weather_data.get("main", {}).get("temp")
    if current_temp is None:
        return False
    
    # Get previous temperature
    last_state = _last_weather_state.get(area_id_str, {})
    last_temp = last_state.get("temperature")
    
    # Update last temperature
    _last_weather_state[area_id_str]["temperature"] = current_temp
    
    # On first check, don't trigger (just record the temperature)
    if last_temp is None:
        logger.info(f"Recording initial temperature {current_temp}°C for area {area_id_str}")
        return False
    
    # Check if threshold is crossed
    if operator == "above":
        # Trigger when temperature crosses above threshold
        return last_temp <= threshold < current_temp
    elif operator == "below":
        # Trigger when temperature crosses below threshold
        return last_temp >= threshold > current_temp
    else:
        logger.warning(f"Unknown operator '{operator}' for area {area_id_str}")
        return False


async def _check_weather_condition(area: Area, weather_data: dict, area_id_str: str) -> bool:
    """Check if weather condition matches the expected condition.
    
    Args:
        area: Area with weather_condition trigger
        weather_data: Current weather data
        area_id_str: Area ID as string
        
    Returns:
        True if condition matches and has changed
    """
    params = area.trigger_params or {}
    expected_condition = params.get("condition", "").lower()
    
    if not expected_condition:
        logger.warning(f"No condition configured for area {area_id_str}")
        return False
    
    current_condition = weather_data.get("weather", [{}])[0].get("main", "").lower()
    
    # Get previous condition
    last_state = _last_weather_state.get(area_id_str, {})
    last_condition = last_state.get("condition")
    
    # Update last condition
    _last_weather_state[area_id_str]["condition"] = current_condition
    
    # Trigger if condition matches and has changed from previous check
    # This prevents triggering continuously while condition persists
    return current_condition == expected_condition and current_condition != last_condition


async def _process_weather_trigger(db: Session, area: Area, weather_data: dict, now: datetime) -> None:
    """Process a weather trigger event and execute the area.
    
    Args:
        db: Database session
        area: Area to execute
        weather_data: Current weather data
        now: Current timestamp
    """
    # Re-attach the Area instance to the current session
    area = db.merge(area)
    area_id_str = str(area.id)
    execution_log = None

    try:
        # Create execution log entry
        execution_log_start = ExecutionLogCreate(
            area_id=area.id,
            status="Started",
            output=None,
            error_message=None,
            step_details={
                "event": {
                    "now": now.isoformat(),
                    "area_id": area_id_str,
                    "user_id": str(area.user_id),
                    "temperature": weather_data.get("main", {}).get("temp"),
                    "condition": weather_data.get("weather", [{}])[0].get("main"),
                }
            }
        )
        execution_log = create_execution_log(db, execution_log_start)

        # Extract weather variables
        variables = _extract_weather_variables(weather_data)

        # Build trigger_data with weather variables
        trigger_data = {
            **variables,
            "now": now.isoformat(),
            "timestamp": now.timestamp(),
            "area_id": area_id_str,
            "user_id": str(area.user_id),
        }

        # Execute area
        result = execute_area(db, area, trigger_data)

        # Update execution log
        execution_log.status = "Success" if result["status"] == "success" else "Failed"
        execution_log.output = f"Weather trigger executed: {result['steps_executed']} step(s)"
        execution_log.error_message = result.get("error")
        execution_log.step_details = {
            "execution_log": result.get("execution_log", []),
            "steps_executed": result["steps_executed"],
            "weather_data": weather_data,
        }
        db.commit()

        logger.info(
            "Weather trigger executed",
            extra={
                "area_id": area_id_str,
                "area_name": area.name,
                "user_id": str(area.user_id),
                "temperature": variables.get("weather.temperature"),
                "condition": variables.get("weather.condition"),
                "status": result["status"],
                "steps_executed": result.get("steps_executed", 0),
            },
        )

    except Exception as e:
        # Update execution log with failure
        if execution_log:
            execution_log.status = "Failed"
            execution_log.error_message = str(e)
            db.commit()

        logger.error(
            "Error executing weather trigger",
            extra={
                "area_id": area_id_str,
                "error": str(e),
            },
            exc_info=True,
        )


def start_weather_scheduler() -> None:
    """Start the weather polling scheduler task."""
    global _weather_scheduler_task

    if _weather_scheduler_task is not None:
        logger.warning("Weather scheduler task already running")
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("No event loop running, cannot start weather scheduler")
        return

    _weather_scheduler_task = loop.create_task(weather_scheduler_task())
    logger.info("Weather scheduler task started")


def stop_weather_scheduler() -> None:
    """Stop the weather polling scheduler task."""
    global _weather_scheduler_task

    if _weather_scheduler_task is not None:
        _weather_scheduler_task.cancel()
        _weather_scheduler_task = None
        logger.info("Weather scheduler task stopped")


def is_weather_scheduler_running() -> bool:
    """Check if the weather scheduler task is running.
    
    Returns:
        True if scheduler is running and not done/cancelled, False otherwise
    """
    global _weather_scheduler_task
    return _weather_scheduler_task is not None and not _weather_scheduler_task.done()


def clear_weather_state() -> None:
    """Clear the in-memory weather state (useful for testing)."""
    global _last_weather_state
    _last_weather_state.clear()


__all__ = [
    "weather_scheduler_task",
    "start_weather_scheduler",
    "is_weather_scheduler_running",
    "stop_weather_scheduler",
    "clear_weather_state",
]
