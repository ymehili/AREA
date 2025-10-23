"""Delay plugin for AREA - Implements pause functionality between steps in automation workflows."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")


async def delay_handler(area: Area, params: dict, event: dict) -> None:
    """Handle delay steps by pausing execution for specified duration.

    Args:
        area: The Area containing the delay step
        params: Configuration parameters for the delay step, including duration and unit
        event: Event data with context about the execution
    """
    # Get duration and unit from config - default to 1 second if not provided
    duration = params.get("duration", 1)
    unit = params.get("unit", "seconds")

    # Convert to seconds based on unit
    if unit == "seconds":
        delay_seconds = duration
    elif unit == "minutes":
        delay_seconds = duration * 60
    elif unit == "hours":
        delay_seconds = duration * 60 * 60
    elif unit == "days":
        delay_seconds = duration * 60 * 60 * 24
    else:
        # Default to seconds if unit is not recognized
        delay_seconds = duration
        logger.warning(
            f"Unrecognized time unit '{unit}' for delay, defaulting to seconds"
        )

    # Log the delay operation
    logger.info(
        f"Delay step executing for Area {area.id}, pausing for {delay_seconds} seconds",
        extra={
            "area_id": str(area.id),
            "user_id": str(area.user_id),
            "delay_duration": delay_seconds,
        },
    )

    # Use async sleep to avoid blocking the event loop
    await asyncio.sleep(delay_seconds)

    logger.info(
        f"Delay step completed for Area {area.id}",
        extra={
            "area_id": str(area.id),
            "user_id": str(area.user_id),
            "delay_duration": delay_seconds,
        },
    )


__all__ = ["delay_handler"]
