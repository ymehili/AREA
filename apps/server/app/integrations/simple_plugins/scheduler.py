"""Background scheduler for time-based Area triggers."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.integrations.simple_plugins.registry import get_plugins_registry
from app.models.area import Area
from app.schemas.execution_log import ExecutionLogCreate
from app.services.execution_logs import create_execution_log
from app.services.step_executor import execute_area

logger = logging.getLogger("area")

# In-memory storage for last run times
_last_run_by_area_id: Dict[str, datetime] = {}
_scheduler_task: asyncio.Task | None = None


def _fetch_due_areas(db: Session) -> list[Area]:
    """Fetch all enabled areas with time-based triggers (sync function for thread pool).

    Args:
        db: Database session

    Returns:
        List of Area objects
    """
    return (
        db.query(Area)
        .filter(
            Area.enabled == True,  # noqa: E712
            Area.trigger_service == "time",
            Area.trigger_action == "every_interval",
        )
        .all()
    )


def is_area_due(
    area: Area, now: datetime, last_run: datetime | None, default_interval: int = 60
) -> bool:
    """Check if an area is due to run based on interval.

    Args:
        area: The Area to check
        now: Current datetime
        last_run: Last run datetime or None
        default_interval: Default interval in seconds if not specified

    Returns:
        True if the area should run now
    """
    if last_run is None:
        return True

    # Get interval from trigger_params or use default
    interval_seconds = default_interval
    if area.trigger_params:
        interval_seconds = area.trigger_params.get("interval_seconds", default_interval)

    # Check if enough time has passed
    elapsed = (now - last_run).total_seconds()
    return elapsed >= interval_seconds


async def scheduler_task() -> None:
    """Background task that checks and executes time-based areas."""
    # Import here to avoid circular imports
    from app.db.session import SessionLocal

    logger.info("Starting area scheduler task")
    registry = get_plugins_registry()

    while True:
        try:
            await asyncio.sleep(1)  # Check every second

            now = datetime.now(timezone.utc)
            db = SessionLocal()

            try:
                # Load all enabled areas with time/every_interval trigger (non-blocking)
                areas = await asyncio.to_thread(_fetch_due_areas, db)

                logger.info(
                    "Scheduler tick",
                    extra={
                        "utc_now": now.isoformat(),
                        "areas_count": len(areas),
                    },
                )

                for area in areas:
                    area_id_str = str(area.id)
                    last_run = _last_run_by_area_id.get(area_id_str)

                    # Check if area is due to run
                    if is_area_due(area, now, last_run):
                        execution_log = None  # Initialize before try block
                        try:
                            # Create execution log entry for start of execution
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
                                        "tick": True,
                                    }
                                }
                            )
                            execution_log = create_execution_log(db, execution_log_start)

                            # Get configured interval for logging
                            interval_seconds = 60
                            if area.trigger_params:
                                interval_seconds = area.trigger_params.get("interval_seconds", 60)

                            # Assemble trigger event data with datetime context
                            trigger_data = {
                                "now": now.isoformat(),
                                "timestamp": now.timestamp(),
                                "year": now.year,
                                "month": now.month,
                                "day": now.day,
                                "hour": now.hour,
                                "minute": now.minute,
                                "second": now.second,
                                "weekday": now.weekday(),
                                "area_id": area_id_str,
                                "user_id": str(area.user_id),
                                "tick": True,
                            }

                            # Execute area using new step executor
                            try:
                                result = execute_area(db, area, trigger_data)

                                # Update last run time
                                _last_run_by_area_id[area_id_str] = now

                                # Update execution log based on result
                                execution_log.status = "Success" if result["status"] == "success" else "Failed"
                                execution_log.output = f"Executed {result['steps_executed']} step(s)"
                                execution_log.error_message = result.get("error")
                                execution_log.step_details = {
                                    "execution_log": result.get("execution_log", []),
                                    "steps_executed": result["steps_executed"],
                                }
                                db.commit()

                                # Log execution with interval for troubleshooting
                                logger.info(
                                    "Area executed",
                                    extra={
                                        "area_id": area_id_str,
                                        "area_name": area.name,
                                        "interval_seconds": interval_seconds,
                                        "status": result["status"],
                                        "steps_executed": result["steps_executed"],
                                    },
                                )
                            except Exception as execution_error:
                                # Update execution log with failure status
                                execution_log.status = "Failed"
                                execution_log.error_message = str(execution_error)
                                db.commit()

                                logger.error(
                                    "Error executing area",
                                    extra={
                                        "area_id": area_id_str,
                                        "error": str(execution_error),
                                    },
                                    exc_info=True,
                                )

                        except Exception as e:
                            logger.error(
                                "Error executing area",
                                extra={
                                    "area_id": area_id_str,
                                    "error": str(e),
                                },
                                exc_info=True,
                            )
                            # Try to update execution log with error status, but don't fail if db operations fail too
                            try:
                                # If execution_log exists, update it with error status
                                if execution_log is not None:
                                    execution_log.status = "Failed"
                                    execution_log.error_message = str(e)
                                    db.commit()
                            except Exception as log_error:
                                logger.error(
                                    "Error updating execution log",
                                    extra={
                                        "area_id": area_id_str,
                                        "error": str(log_error),
                                    },
                                    exc_info=True,
                                )

            finally:
                db.close()

        except asyncio.CancelledError:
            # Handle cancellation explicitly - let it propagate
            logger.info("Scheduler task cancelled, shutting down gracefully")
            break  # Exit the while loop

        except Exception as e:  # pragma: no cover
            logger.error("Scheduler task error", extra={"error": str(e)}, exc_info=True)
            await asyncio.sleep(5)  # Back off on error

    logger.info("Scheduler task stopped")


def start_scheduler() -> None:
    """Start the background scheduler task."""
    global _scheduler_task

    if _scheduler_task is not None:
        logger.warning("Scheduler task already running")
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.error("No event loop running, cannot start scheduler")
        return

    _scheduler_task = loop.create_task(scheduler_task())
    logger.info("Scheduler task started")


def stop_scheduler() -> None:
    """Stop the background scheduler task."""
    global _scheduler_task

    if _scheduler_task is not None:
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("Scheduler task stopped")


def clear_last_run_state() -> None:
    """Clear the in-memory last run state (useful for testing)."""
    global _last_run_by_area_id
    _last_run_by_area_id.clear()


__all__ = [
    "scheduler_task",
    "start_scheduler",
    "stop_scheduler",
    "is_area_due",
    "clear_last_run_state",
]