"""Multi-step area execution engine with support for delay steps and state persistence."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.integrations.simple_plugins.registry import get_plugins_registry
from app.models.area import Area
from app.models.area_step import AreaStep
from app.schemas.execution_log import ExecutionLogCreate
from app.services.area_steps import get_steps_by_area
from app.services.execution_logs import create_execution_log

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")


class AreaExecutionState:
    """Represents the execution state of a multi-step area."""
    
    def __init__(self, area_id: str, current_step_index: int = 0, start_time: datetime | None = None):
        self.area_id = area_id
        self.current_step_index = current_step_index
        self.start_time = start_time or datetime.now(timezone.utc)
        # Additional state fields can be added as needed


class ExecutionEngine:
    """Engine for executing multi-step areas with support for delays and state persistence."""
    
    def __init__(self, db: Session):
        self.db = db
        self.registry = get_plugins_registry()
    
    async def execute_area_steps(self, area: Area, event: dict) -> bool:
        """Execute all steps in an area in order, handling delays appropriately.
        
        Args:
            area: The area to execute
            event: Event data to pass to each step
            
        Returns:
            True if execution completed successfully, False otherwise
        """
        steps = get_steps_by_area(self.db, area.id)
        
        if not steps:
            logger.warning(f"No steps found for area {area.id}, nothing to execute")
            return True
        
        # Sort steps by order to ensure proper execution sequence
        sorted_steps = sorted(steps, key=lambda step: step.order)
        
        logger.info(
            f"Starting execution of {len(sorted_steps)} steps for area {area.id}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "step_count": len(sorted_steps),
            }
        )
        
        # Create execution log entry for start of execution
        execution_log_start = ExecutionLogCreate(
            area_id=area.id,
            status="Started",
            output=None,
            error_message=None,
            step_details={
                "event": event,
                "step_count": len(sorted_steps),
            }
        )
        execution_log = create_execution_log(self.db, execution_log_start)
        
        try:
            # Execute each step in sequence
            for idx, step in enumerate(sorted_steps):
                step_label = f"Step {idx + 1}/{len(sorted_steps)} (order {step.order})"
                
                logger.info(
                    f"Executing {step_label} for area {area.id}",
                    extra={
                        "area_id": str(area.id),
                        "user_id": str(area.user_id),
                        "step_order": step.order,
                        "step_type": step.step_type,
                        "step_service": step.service,
                        "step_action": step.action,
                    }
                )
                
                # Update execution log with current step
                execution_log.step_details["current_step"] = {
                    "order": step.order,
                    "type": step.step_type,
                    "service": step.service,
                    "action": step.action,
                }
                self.db.commit()
                
                # Execute the step based on its type
                if step.step_type == "delay":
                    # Handle delay step
                    await self._execute_delay_step(area, step, event)
                elif step.step_type in ["action", "reaction"]:
                    # Handle action/reaction step
                    await self._execute_action_reaction_step(area, step, event)
                elif step.step_type in ["condition", "trigger"]:
                    # Handle condition and trigger steps (placeholder for future implementation)
                    logger.info(
                        f"{step.step_type.title()} step not yet implemented for area {area.id}, step order {step.order}",
                        extra={
                            "area_id": str(area.id),
                            "user_id": str(area.user_id),
                            "step_order": step.order,
                        }
                    )
                else:
                    logger.warning(
                        f"Unknown step type '{step.step_type}' for area {area.id}, step order {step.order}",
                        extra={
                            "area_id": str(area.id),
                            "user_id": str(area.user_id),
                            "step_order": step.order,
                            "step_type": step.step_type,
                        }
                    )
                    execution_log.status = "Failed"
                    execution_log.error_message = f"Unknown step type '{step.step_type}'"
                    self.db.commit()
                    return False
            
            # Update execution log with success status
            execution_log.status = "Success"
            execution_log.step_details["completed"] = True
            execution_log.step_details["completed_at"] = datetime.now(timezone.utc).isoformat()
            self.db.commit()
            
            logger.info(
                f"Area {area.id} execution completed successfully",
                extra={
                    "area_id": str(area.id),
                    "user_id": str(area.user_id),
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Error executing area {area.id}",
                extra={
                    "area_id": str(area.id),
                    "user_id": str(area.user_id),
                    "error": str(e),
                },
                exc_info=True
            )
            
            # Update execution log with failure status
            execution_log.status = "Failed"
            execution_log.error_message = str(e)
            self.db.commit()
            
            return False
    
    async def _execute_delay_step(self, area: Area, step: AreaStep, event: dict) -> None:
        """Execute a delay step."""
        if step.step_type != "delay":
            raise ValueError(f"Expected delay step, got {step.step_type}")
        
        # Get delay configuration, defaulting to 1 second
        config = step.config or {}
        duration = config.get("duration", 1)
        unit = config.get("unit", "seconds")
        
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
            logger.warning(f"Unrecognized time unit '{unit}' for delay in area {area.id}, defaulting to seconds")
        
        logger.info(
            f"Delay step executing for Area {area.id}, pausing for {delay_seconds} seconds",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "delay_duration": delay_seconds,
            }
        )
        
        # Use async sleep to avoid blocking the event loop
        await asyncio.sleep(delay_seconds)
        
        logger.info(
            f"Delay step completed for Area {area.id}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "delay_duration": delay_seconds,
            }
        )
    
    async def _execute_action_reaction_step(self, area: Area, step: AreaStep, event: dict) -> None:
        """Execute an action or reaction step."""
        if step.step_type not in ["action", "reaction"]:
            raise ValueError(f"Expected action or reaction step, got {step.step_type}")
        
        if not step.service or not step.action:
            raise ValueError(f"Action/reaction step missing service or action: service={step.service}, action={step.action}")
        
        # Get reaction handler
        handler = self.registry.get_reaction_handler(step.service, step.action)
        
        if not handler:
            error_msg = f"No handler found for {step.step_type} {step.service}.{step.action}"
            logger.warning(
                error_msg,
                extra={
                    "area_id": str(area.id),
                    "user_id": str(area.user_id),
                    "step_type": step.step_type,
                    "service": step.service,
                    "action": step.action,
                }
            )
            raise ValueError(error_msg)
        
        # Execute handler with step config as params
        step_params = step.config or {}
        
        # Add area and event context to params
        step_params_with_context = {
            **step_params,
            "area_id": str(area.id),
            "user_id": str(area.user_id),
        }
        
        logger.info(
            f"Executing {step.step_type} step for Area {area.id}: {step.service}.{step.action}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "step_service": step.service,
                "step_action": step.action,
            }
        )
        
        # Execute the handler
        handler(area, step_params_with_context, event)


async def execute_area_steps(db: Session, area: Area, event: dict) -> bool:
    """Public function to execute multi-step areas.
    
    Args:
        db: Database session
        area: The area to execute
        event: Event data to pass to each step
        
    Returns:
        True if execution completed successfully, False otherwise
    """
    engine = ExecutionEngine(db)
    return await engine.execute_area_steps(area, event)


__all__ = ["execute_area_steps", "AreaExecutionState", "ExecutionEngine"]