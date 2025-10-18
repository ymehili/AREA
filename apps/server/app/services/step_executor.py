"""Step-by-step execution engine for multi-step AREA workflows.

This module provides the core execution engine that:
- Traverses multi-step workflow graphs
- Evaluates conditional branches
- Executes actions/reactions via plugin registry
- Maintains execution context across steps
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.integrations.simple_plugins.registry import get_plugins_registry
from app.models.area import Area
from app.models.area_step import AreaStep
from app.services.condition_evaluator import (
    ConditionEvaluationError,
    evaluate_condition,
)

logger = logging.getLogger("area")


class StepExecutionError(Exception):
    """Raised when step execution fails."""

    pass


class StepExecutor:
    """Executor for multi-step AREA workflows."""

    def __init__(self, db: Session, area: Area) -> None:
        """Initialize step executor for an area.

        Args:
            db: Database session
            area: Area to execute
        """
        self.db = db
        self.area = area
        self.registry = get_plugins_registry()
        self.execution_context: Dict[str, Any] = {}
        self.execution_log: List[Dict[str, Any]] = []

    def execute(self, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the area workflow starting from trigger.

        Args:
            trigger_data: Data from the trigger event (e.g., {"now": "...", "tick": True})

        Returns:
            Dictionary with execution results:
            {
                "status": "success" | "failed" | "skipped",
                "steps_executed": int,
                "execution_log": [...],
                "error": str | None
            }

        Raises:
            StepExecutionError: If execution fails critically
        """
        try:
            # Initialize execution context
            self.execution_context = {
                "trigger": trigger_data,
                "area_id": str(self.area.id),
                "user_id": str(self.area.user_id),
                "executed_steps": [],
            }

            # Check if area has steps (multi-step workflow)
            if self.area.steps and len(self.area.steps) > 0:
                return self._execute_multi_step_workflow()
            else:
                # Legacy single-step area (backward compatibility)
                return self._execute_legacy_workflow()

        except Exception as e:
            logger.error(
                "Area execution failed",
                extra={
                    "area_id": str(self.area.id),
                    "error": str(e),
                },
                exc_info=True,
            )
            return {
                "status": "failed",
                "steps_executed": len(self.execution_log),
                "execution_log": self.execution_log,
                "error": str(e),
            }

    def _execute_multi_step_workflow(self) -> Dict[str, Any]:
        """Execute multi-step workflow by traversing the step graph.

        Returns:
            Execution result dictionary
        """
        # Find the trigger step (should be first step with order=0)
        trigger_step = next(
            (step for step in self.area.steps if step.step_type == "trigger"),
            None,
        )

        if not trigger_step:
            # No trigger step, start with first step in order
            if self.area.steps:
                trigger_step = self.area.steps[0]
            else:
                return {
                    "status": "failed",
                    "steps_executed": 0,
                    "execution_log": self.execution_log,
                    "error": "No steps found in area",
                }

        # Execute starting from trigger step
        self._execute_step(trigger_step)

        # Determine overall status
        has_errors = any(
            log.get("status") == "failed" for log in self.execution_log
        )
        status = "failed" if has_errors else "success"
        
        # Log area execution summary
        logger.info(
            "Area execution completed",
            extra={
                "area_id": str(self.area.id),
                "area_name": self.area.name,
                "user_id": str(self.area.user_id),
                "status": status,
                "steps_executed": len(self.execution_log),
                "steps_failed": len([log for log in self.execution_log if log.get("status") == "failed"]),
                "execution_log": self.execution_log,
            },
        )

        return {
            "status": status,
            "steps_executed": len(self.execution_log),
            "execution_log": self.execution_log,
            "error": None,
        }

    def _execute_step(self, step: AreaStep) -> bool:
        """Execute a single step and follow its connections.

        Args:
            step: Step to execute

        Returns:
            True if step executed successfully, False otherwise
        """
        step_id = str(step.id)
        step_log = {
            "step_id": step_id,
            "step_type": step.step_type,
            "service": step.service,
            "action": step.action,
            "status": "started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            "Executing step",
            extra={
                "area_id": str(self.area.id),
                "step_id": step_id,
                "step_type": step.step_type,
            },
        )

        try:
            # Execute step based on type
            if step.step_type == "trigger":
                # Trigger step - just pass through, data already in context
                step_log["status"] = "success"
                step_log["output"] = "Trigger activated"
                self.execution_log.append(step_log)
                
                logger.info(
                    "Trigger step executed successfully",
                    extra={
                        "area_id": str(self.area.id),
                        "step_id": step_id,
                        "step_type": step.step_type,
                        "service": step.service,
                        "action": step.action,
                    },
                )

                # Follow connections to next steps
                self._follow_step_connections(step)
                return True

            elif step.step_type == "condition":
                # Condition step - evaluate and branch
                result = self._execute_condition_step(step, step_log)
                return result

            elif step.step_type in ["action", "reaction"]:
                # Action/Reaction step - execute handler
                result = self._execute_action_step(step, step_log)
                if result:
                    # Continue to next steps
                    self._follow_step_connections(step)
                return result

            elif step.step_type == "delay":
                # Delay step - log for now (full async delay requires job queue)
                step_log["status"] = "success"
                step_log["output"] = f"Delay step (not implemented yet): {step.config}"
                self.execution_log.append(step_log)
                logger.warning(
                    "Delay step not yet implemented, skipping",
                    extra={
                        "area_id": str(self.area.id),
                        "step_id": step_id,
                        "step_type": step.step_type,
                    },
                )
                # Continue to next steps
                self._follow_step_connections(step)
                return True

            else:
                step_log["status"] = "failed"
                step_log["error"] = f"Unknown step type: {step.step_type}"
                self.execution_log.append(step_log)
                logger.error(
                    "Unknown step type encountered",
                    extra={
                        "area_id": str(self.area.id),
                        "step_id": step_id,
                        "step_type": step.step_type,
                    },
                )
                return False

        except Exception as e:
            step_log["status"] = "failed"
            step_log["error"] = str(e)
            self.execution_log.append(step_log)
            logger.error(
                "Step execution failed",
                extra={
                    "area_id": str(self.area.id),
                    "step_id": step_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return False

    def _execute_condition_step(
        self, step: AreaStep, step_log: Dict[str, Any]
    ) -> bool:
        """Execute a condition step and branch based on result.

        Args:
            step: Condition step to execute
            step_log: Log entry for this step

        Returns:
            True if condition evaluated successfully, False otherwise
        """
        try:
            # Get condition configuration
            condition_config = step.config or {}

            # Evaluate condition
            result = evaluate_condition(condition_config, self.execution_context)

            step_log["status"] = "success"
            step_log["output"] = f"Condition evaluated to: {result}"
            step_log["condition_result"] = result
            self.execution_log.append(step_log)

            logger.info(
                "Condition evaluated",
                extra={
                    "area_id": str(self.area.id),
                    "step_id": str(step.id),
                    "result": result,
                },
            )

            # Follow appropriate branch based on result
            if result:
                # Follow TRUE branch (targets)
                self._follow_step_connections(step, branch="true")
            else:
                # Follow FALSE branch (elseBranch)
                self._follow_step_connections(step, branch="false")

            return True

        except ConditionEvaluationError as e:
            step_log["status"] = "failed"
            step_log["error"] = f"Condition evaluation error: {e}"
            self.execution_log.append(step_log)
            logger.error(
                "Condition evaluation failed",
                extra={
                    "area_id": str(self.area.id),
                    "step_id": str(step.id),
                    "error": str(e),
                },
                exc_info=True,
            )
            return False

    def _execute_action_step(
        self, step: AreaStep, step_log: Dict[str, Any]
    ) -> bool:
        """Execute an action or reaction step.

        Args:
            step: Action/reaction step to execute
            step_log: Log entry for this step

        Returns:
            True if action executed successfully, False otherwise
        """
        try:
            # Get handler for this action
            handler = self.registry.get_reaction_handler(
                step.service, step.action
            )

            if not handler:
                step_log["status"] = "failed"
                step_log[
                    "error"
                ] = f"No handler found for {step.service}.{step.action}"
                self.execution_log.append(step_log)
                logger.warning(
                    "No handler found for action",
                    extra={
                        "area_id": str(self.area.id),
                        "step_id": str(step.id),
                        "service": step.service,
                        "action": step.action,
                    },
                )
                return False

            # Prepare parameters for handler
            params = step.config or {}
            
            # Import variable resolver and substitute variables
            from app.services.variable_resolver import substitute_variables_in_params, extract_variables_by_service
            trigger_data = self.execution_context.get('trigger', {})

            # Use service-specific extractor based on trigger service, not action service
            # The trigger data should be parsed according to the trigger service type
            trigger_service = self.area.trigger_service
            variables_from_context = extract_variables_by_service(trigger_data, trigger_service)

            params = substitute_variables_in_params(params, variables_from_context)

            # Execute handler - pass the trigger_data as the event parameter
            logger.info(
                "Executing action handler",
                extra={
                    "area_id": str(self.area.id),
                    "step_id": str(step.id),
                    "service": step.service,
                    "action": step.action,
                    "params": params,
                },
            )
            
            # Execute handler - it may modify trigger_data (e.g., weather adds weather_data)
            handler(self.area, params, trigger_data)

            step_log["status"] = "success"
            step_log["output"] = f"Executed {step.service}.{step.action}"
            step_log["params_used"] = params
            
            # If this is a weather action, include weather data in the log
            # Check after handler execution as the handler adds this data
            if step.service == "weather":
                logger.info(
                    "Weather action executed, checking for weather_data",
                    extra={
                        "area_id": str(self.area.id),
                        "step_id": str(step.id),
                        "trigger_data_keys": list(trigger_data.keys()),
                        "has_weather_data": "weather_data" in trigger_data,
                    }
                )
                if "weather_data" in trigger_data:
                    step_log["weather_data"] = trigger_data["weather_data"]
                    logger.info("Weather data added to step log", extra={"weather_data": trigger_data["weather_data"]})
            
            # If this is an openai action, include openai data in the log
            # Check after handler execution as the handler adds this data
            if step.service == "openai":
                logger.info(
                    "OpenAI action executed, checking for openai_data",
                    extra={
                        "area_id": str(self.area.id),
                        "step_id": str(step.id),
                        "trigger_data_keys": list(trigger_data.keys()),
                        "has_openai_data": "openai_data" in trigger_data,
                    }
                )
                if "openai_data" in trigger_data:
                    step_log["openai_data"] = trigger_data["openai_data"]
                    # Also update the output to show the actual response
                    if "response" in trigger_data["openai_data"]:
                        step_log["output"] = trigger_data["openai_data"]["response"]
                    logger.info("OpenAI data added to step log", extra={"openai_data": trigger_data["openai_data"]})
            
            self.execution_log.append(step_log)

            logger.info(
                "Action executed successfully",
                extra={
                    "area_id": str(self.area.id),
                    "step_id": str(step.id),
                    "service": step.service,
                    "action": step.action,
                    "params": params,
                },
            )
            return True

        except Exception as e:
            step_log["status"] = "failed"
            step_log["error"] = str(e)
            self.execution_log.append(step_log)
            logger.error(
                "Action execution failed",
                extra={
                    "area_id": str(self.area.id),
                    "step_id": str(step.id),
                    "error": str(e),
                },
                exc_info=True,
            )
            return False

    def _follow_step_connections(
        self, step: AreaStep, branch: Optional[str] = None
    ) -> None:
        """Follow connections from a step to execute next steps.

        Args:
            step: Current step
            branch: Branch to follow ("true", "false", or None for default)
        """
        config = step.config or {}

        # Get target step IDs based on branch
        if branch == "false":
            # Follow else branch for conditions
            target_ids = config.get("elseBranch", [])
        else:
            # Default: follow targets
            target_ids = config.get("targets", [])

        if not target_ids:
            logger.debug(
                "No target steps to follow",
                extra={
                    "area_id": str(self.area.id),
                    "step_id": str(step.id),
                    "branch": branch,
                },
            )
            return

        # Execute each target step
        for target_id in target_ids:
            # Find target step by ID
            target_step = next(
                (s for s in self.area.steps if str(s.id) == str(target_id)),
                None,
            )

            if target_step:
                # Check if we've already executed this step (prevent infinite loops)
                executed_ids = [
                    log["step_id"] for log in self.execution_log
                ]
                if str(target_step.id) in executed_ids:
                    logger.warning(
                        "Step already executed, skipping to prevent loop",
                        extra={
                            "area_id": str(self.area.id),
                            "step_id": str(target_step.id),
                        },
                    )
                    continue

                # Execute the target step
                self._execute_step(target_step)
            else:
                logger.warning(
                    "Target step not found",
                    extra={
                        "area_id": str(self.area.id),
                        "target_id": target_id,
                    },
                )

    def _execute_legacy_workflow(self) -> Dict[str, Any]:
        """Execute legacy single-step workflow (backward compatibility).

        Returns:
            Execution result dictionary
        """
        step_log = {
            "step_id": "legacy",
            "step_type": "reaction",
            "service": self.area.reaction_service,
            "action": self.area.reaction_action,
            "status": "started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Get reaction handler
            handler = self.registry.get_reaction_handler(
                self.area.reaction_service, self.area.reaction_action
            )

            if not handler:
                step_log["status"] = "failed"
                step_log[
                    "error"
                ] = f"No handler found for {self.area.reaction_service}.{self.area.reaction_action}"
                self.execution_log.append(step_log)
                return {
                    "status": "failed",
                    "steps_executed": 1,
                    "execution_log": self.execution_log,
                    "error": step_log["error"],
                }

            # Import variable resolver and substitute variables
            from app.services.variable_resolver import substitute_variables_in_params, extract_variables_by_service
            trigger_data = self.execution_context.get("trigger", {})
            
            # Use service-specific extractor based on trigger service, not reaction service
            variables_from_context = extract_variables_by_service(trigger_data, self.area.trigger_service)
            
            # Process reaction params with variable substitution
            reaction_params = self.area.reaction_params or {}
            reaction_params = substitute_variables_in_params(reaction_params, variables_from_context)
            
            # Execute reaction with params
            handler(
                self.area,
                reaction_params,
                trigger_data,  # Pass original trigger data to handler
            )

            step_log["status"] = "success"
            step_log[
                "output"
            ] = f"Executed {self.area.reaction_service}.{self.area.reaction_action}"
            self.execution_log.append(step_log)

            return {
                "status": "success",
                "steps_executed": 1,
                "execution_log": self.execution_log,
                "error": None,
            }

        except Exception as e:
            step_log["status"] = "failed"
            step_log["error"] = str(e)
            self.execution_log.append(step_log)
            return {
                "status": "failed",
                "steps_executed": 1,
                "execution_log": self.execution_log,
                "error": str(e),
            }


def execute_area(db: Session, area: Area, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an area workflow with the given trigger data.

    Args:
        db: Database session
        area: Area to execute
        trigger_data: Data from trigger event

    Returns:
        Execution result dictionary
    """
    executor = StepExecutor(db, area)
    return executor.execute(trigger_data)


__all__ = [
    "StepExecutor",
    "StepExecutionError",
    "execute_area",
]
