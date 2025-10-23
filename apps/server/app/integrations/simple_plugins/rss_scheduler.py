"""RSS polling scheduler for trigger-based automation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.variable_extractor import extract_variables_by_service
from app.models.area import Area
from app.schemas.execution_log import ExecutionLogCreate
from app.services.execution_logs import create_execution_log
from app.services.step_executor import execute_area
from app.integrations.simple_plugins.rss_plugin import rss_feed_manager
from app.integrations.simple_plugins.registry import get_handler

logger = logging.getLogger("area")

# In-memory storage for polling state
_rss_scheduler_task: asyncio.Task | None = None

# Default polling interval (configurable via settings)
RSS_POLLING_INTERVAL = getattr(settings, "RSS_POLLING_INTERVAL", 300)  # 5 minutes


def _fetch_due_rss_areas(db: Session) -> list[Area]:
    """Fetch all enabled areas with RSS triggers.

    Args:
        db: Database session

    Returns:
        List of Area objects
    """
    return (
        db.query(Area)
        .filter(
            Area.enabled == True,  # noqa: E712
            Area.trigger_service == "rss",
            Area.trigger_action.in_(["new_item", "keyword_detected"]),
        )
        .all()
    )


async def _process_rss_trigger(
    db: Session, area: Area, trigger_data: dict, now: datetime
) -> None:
    """Process an RSS trigger event and execute the area.

    Args:
        db: Database session
        area: Area to execute
        trigger_data: RSS trigger data
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
                    "trigger_service": "rss",
                    "trigger_action": area.trigger_action,
                    "feed_url": trigger_data.get("rss.feed_url", ""),
                }
            },
        )
        execution_log = create_execution_log(db, execution_log_start)

        # Extract RSS variables using the service-specific extractor
        variables = extract_variables_by_service(trigger_data, "rss")

        # Build trigger_data with RSS variables
        full_trigger_data = {
            **variables,  # Include all extracted rss.* variables
            "now": now.isoformat(),
            "timestamp": now.timestamp(),
            "area_id": area_id_str,
            "user_id": str(area.user_id),
        }

        # Execute area
        result = execute_area(db, area, full_trigger_data)

        # Update execution log
        execution_log.status = "Success" if result["status"] == "success" else "Failed"
        execution_log.output = (
            f"RSS trigger executed: {result['steps_executed']} step(s)"
        )
        execution_log.error_message = result.get("error")
        execution_log.step_details = {
            "execution_log": result.get("execution_log", []),
            "steps_executed": result["steps_executed"],
            "trigger_service": "rss",
            "trigger_action": area.trigger_action,
            "feed_url": trigger_data.get("rss.feed_url", ""),
            "items_processed": trigger_data.get("rss_items_count", 0),
        }
        db.commit()

        logger.info(
            "RSS trigger executed",
            extra={
                "area_id": area_id_str,
                "area_name": area.name,
                "user_id": str(area.user_id),
                "trigger_action": area.trigger_action,
                "feed_url": trigger_data.get("rss.feed_url", ""),
                "status": result["status"],
                "steps_executed": result.get("steps_executed", 0),
                "items_processed": trigger_data.get("rss_items_count", 0),
            },
        )

    except Exception as e:
        # Update execution log with failure
        if execution_log:
            execution_log.status = "Failed"
            execution_log.error_message = str(e)
            db.commit()

        logger.error(
            "Error executing RSS trigger",
            extra={
                "area_id": area_id_str,
                "trigger_action": area.trigger_action,
                "feed_url": trigger_data.get("rss.feed_url", ""),
                "error": str(e),
            },
            exc_info=True,
        )


async def rss_scheduler_task() -> None:
    """Background task that polls RSS feeds for new items based on AREA triggers."""
    from app.db.session import SessionLocal

    logger.info("Starting RSS polling scheduler task")

    while True:
        try:
            # Poll at configurable intervals
            await asyncio.sleep(RSS_POLLING_INTERVAL)

            now = datetime.now(timezone.utc)

            # Fetch all enabled RSS areas using a scoped session
            with SessionLocal() as db:
                areas = await asyncio.to_thread(_fetch_due_rss_areas, db)

                logger.info(
                    "RSS scheduler tick",
                    extra={
                        "utc_now": now.isoformat(),
                        "areas_count": len(areas),
                        "polling_interval": RSS_POLLING_INTERVAL,
                    },
                )

            # Process each area with its own scoped session
            for area in areas:
                area_id_str = str(area.id)

                try:
                    # Use scoped session for this area's processing
                    with SessionLocal() as db:
                        # Get the appropriate RSS handler
                        handler = get_handler("rss", area.trigger_action)
                        if not handler:
                            logger.error(
                                f"No RSS handler found for action: {area.trigger_action}",
                                extra={
                                    "area_id": area_id_str,
                                    "trigger_action": area.trigger_action,
                                },
                            )
                            continue

                        # Prepare event data for handler
                        event_data = {}

                        # Execute the RSS handler (this will detect new items and populate event_data)
                        await handler(area, area.trigger_params or {}, event_data, db)

                        # Check if handler found and processed new RSS items
                        rss_items_count = 0
                        for key in event_data.keys():
                            if key.startswith("rss.") and not key.endswith(
                                ("_feed_title", "_feed_url", "_feed_description")
                            ):
                                # This indicates RSS items were processed
                                rss_items_count = max(rss_items_count, 1)

                        if rss_items_count > 0:
                            # Add metadata about the processing
                            event_data["rss.feed_url"] = area.trigger_params.get(
                                "feed_url", ""
                            )
                            event_data["rss_items_count"] = rss_items_count
                            event_data["rss_trigger_action"] = area.trigger_action

                            logger.info(
                                f"RSS handler processed {rss_items_count} item(s) for area {area_id_str}",
                                extra={
                                    "area_id": area_id_str,
                                    "area_name": area.name,
                                    "user_id": str(area.user_id),
                                    "trigger_action": area.trigger_action,
                                    "feed_url": area.trigger_params.get("feed_url", ""),
                                    "items_processed": rss_items_count,
                                },
                            )

                            # Process the RSS trigger (execute reactions)
                            await _process_rss_trigger(db, area, event_data, now)

                        else:
                            # No new items found, just log for monitoring
                            logger.debug(
                                f"No new RSS items for area {area_id_str}",
                                extra={
                                    "area_id": area_id_str,
                                    "area_name": area.name,
                                    "trigger_action": area.trigger_action,
                                    "feed_url": area.trigger_params.get("feed_url", ""),
                                },
                            )

                except Exception as e:
                    logger.error(
                        "Error processing RSS area",
                        extra={
                            "area_id": area_id_str,
                            "trigger_action": area.trigger_action,
                            "feed_url": area.trigger_params.get("feed_url", "")
                            if area.trigger_params
                            else None,
                            "error": str(e),
                        },
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            logger.info("RSS scheduler task cancelled, shutting down gracefully")
            break

        except Exception as e:
            logger.error(
                "RSS scheduler task error", extra={"error": str(e)}, exc_info=True
            )
            await asyncio.sleep(RSS_POLLING_INTERVAL)  # Back off on error

    logger.info("RSS scheduler task stopped")


def start_rss_scheduler() -> None:
    """Start the RSS polling scheduler task."""
    global _rss_scheduler_task

    if _rss_scheduler_task is not None:
        logger.warning("RSS scheduler task already running")
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("No event loop running, cannot start RSS scheduler")
        return

    _rss_scheduler_task = loop.create_task(rss_scheduler_task())
    logger.info("RSS scheduler task started")


def stop_rss_scheduler() -> None:
    """Stop the RSS polling scheduler task."""
    global _rss_scheduler_task

    if _rss_scheduler_task is not None:
        _rss_scheduler_task.cancel()
        _rss_scheduler_task = None
        logger.info("RSS scheduler task stopped")


def is_rss_scheduler_running() -> bool:
    """Check if the RSS scheduler task is running.

    Returns:
        True if scheduler is running and not done/cancelled, False otherwise
    """
    global _rss_scheduler_task
    return _rss_scheduler_task is not None and not _rss_scheduler_task.done()


def clear_rss_cache() -> None:
    """Clear the RSS feed manager cache (useful for testing)."""
    global rss_feed_manager
    if rss_feed_manager:
        rss_feed_manager.cache.clear()
        rss_feed_manager.seen_items.clear()
    logger.info("RSS cache cleared")


__all__ = [
    "rss_scheduler_task",
    "start_rss_scheduler",
    "is_rss_scheduler_running",
    "stop_rss_scheduler",
    "clear_rss_cache",
]
