"""Tests for step executor service."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.area import Area
from app.models.area_step import AreaStep
from app.services.step_executor import StepExecutor, execute_area


class TestStepExecutor:
    """Tests for StepExecutor class."""

    def test_execute_legacy_workflow(self, db_session: Session):
        """Test executing legacy single-step workflow."""
        # Create area without steps (legacy format)
        user_id = uuid.uuid4()
        area = Area(
            user_id=user_id,
            name="Legacy Test Area",
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="debug",
            reaction_action="log",
            reaction_params={"message": "Legacy test"},
            enabled=True,
        )
        db_session.add(area)
        db_session.commit()

        # Execute area
        executor = StepExecutor(db_session, area)
        trigger_data = {"now": "2024-01-01T12:00:00Z", "tick": True}
        result = executor.execute(trigger_data)

        # Verify result
        assert result["status"] == "success"
        assert result["steps_executed"] == 1
        assert result["error"] is None
        assert len(result["execution_log"]) == 1
        assert result["execution_log"][0]["status"] == "success"

    def test_execute_single_step_workflow(self, db_session: Session):
        """Test executing workflow with single action step."""
        # Create area with single step
        user_id = uuid.uuid4()
        area = Area(
            user_id=user_id,
            name="Single Step Area",
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="debug",
            reaction_action="log",
            enabled=True,
        )
        db_session.add(area)
        db_session.commit()

        # Add trigger and action steps
        trigger_step = AreaStep(
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="time",
            action="every_interval",
            config={"targets": []},  # Will add action step ID after creation
        )
        db_session.add(trigger_step)
        db_session.flush()

        action_step = AreaStep(
            area_id=area.id,
            step_type="action",
            order=1,
            service="debug",
            action="log",
            config={"message": "Test log"},
        )
        db_session.add(action_step)
        db_session.flush()

        # Update trigger to point to action
        trigger_step.config = {"targets": [str(action_step.id)]}
        db_session.commit()
        db_session.refresh(area)

        # Execute area
        executor = StepExecutor(db_session, area)
        trigger_data = {"now": "2024-01-01T12:00:00Z", "tick": True}
        result = executor.execute(trigger_data)

        # Verify result
        assert result["status"] == "success"
        assert result["steps_executed"] == 2
        assert len(result["execution_log"]) == 2
        assert result["execution_log"][0]["step_type"] == "trigger"
        assert result["execution_log"][1]["step_type"] == "action"

    def test_execute_workflow_with_condition_true(self, db_session: Session):
        """Test executing workflow where condition evaluates to true."""
        # Create area
        user_id = uuid.uuid4()
        area = Area(
            user_id=user_id,
            name="Condition Test Area",
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="debug",
            reaction_action="log",
            enabled=True,
        )
        db_session.add(area)
        db_session.commit()

        # Add steps: trigger -> condition -> action
        trigger_step = AreaStep(
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="time",
            action="every_interval",
            config={},
        )
        db_session.add(trigger_step)
        db_session.flush()

        condition_step = AreaStep(
            area_id=area.id,
            step_type="condition",
            order=1,
            config={
                "conditionType": "expression",
                "expression": "trigger.minute % 2 == 0",
            },
        )
        db_session.add(condition_step)
        db_session.flush()

        action_step = AreaStep(
            area_id=area.id,
            step_type="action",
            order=2,
            service="debug",
            action="log",
            config={"message": "Condition was true"},
        )
        db_session.add(action_step)
        db_session.flush()

        # Connect steps
        trigger_step.config = {"targets": [str(condition_step.id)]}
        condition_step.config["targets"] = [str(action_step.id)]
        flag_modified(condition_step, "config")
        db_session.commit()
        db_session.refresh(area)

        # Execute with even minute (condition should be true)
        executor = StepExecutor(db_session, area)
        trigger_data = {"minute": 42, "tick": True}
        result = executor.execute(trigger_data)

        # Verify result
        assert result["status"] == "success"
        assert result["steps_executed"] == 3
        assert result["execution_log"][1]["condition_result"] is True
        assert result["execution_log"][2]["step_type"] == "action"

    def test_execute_workflow_with_condition_false(self, db_session: Session):
        """Test executing workflow where condition evaluates to false."""
        # Create area
        user_id = uuid.uuid4()
        area = Area(
            user_id=user_id,
            name="Condition False Test",
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="debug",
            reaction_action="log",
            enabled=True,
        )
        db_session.add(area)
        db_session.commit()

        # Add steps: trigger -> condition -> action
        trigger_step = AreaStep(
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="time",
            action="every_interval",
            config={},
        )
        db_session.add(trigger_step)
        db_session.flush()

        condition_step = AreaStep(
            area_id=area.id,
            step_type="condition",
            order=1,
            config={
                "conditionType": "expression",
                "expression": "trigger.minute % 2 == 0",
                "targets": [],  # No action on true
            },
        )
        db_session.add(condition_step)
        db_session.commit()

        # Connect trigger to condition
        trigger_step.config = {"targets": [str(condition_step.id)]}
        db_session.commit()
        db_session.refresh(area)

        # Execute with odd minute (condition should be false)
        executor = StepExecutor(db_session, area)
        trigger_data = {"minute": 43, "tick": True}
        result = executor.execute(trigger_data)

        # Verify result
        assert result["status"] == "success"
        assert result["steps_executed"] == 2  # Only trigger and condition
        assert result["execution_log"][1]["condition_result"] is False

    def test_execute_workflow_with_else_branch(self, db_session: Session):
        """Test executing workflow with condition else branch."""
        # Create area
        user_id = uuid.uuid4()
        area = Area(
            user_id=user_id,
            name="Else Branch Test",
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="debug",
            reaction_action="log",
            enabled=True,
        )
        db_session.add(area)
        db_session.commit()

        # Add steps: trigger -> condition -> true_action / false_action
        trigger_step = AreaStep(
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="time",
            action="every_interval",
            config={},
        )
        db_session.add(trigger_step)
        db_session.flush()

        condition_step = AreaStep(
            area_id=area.id,
            step_type="condition",
            order=1,
            config={
                "conditionType": "expression",
                "expression": "trigger.minute % 2 == 0",
            },
        )
        db_session.add(condition_step)
        db_session.flush()

        true_action = AreaStep(
            area_id=area.id,
            step_type="action",
            order=2,
            service="debug",
            action="log",
            config={"message": "Even minute"},
        )
        db_session.add(true_action)
        db_session.flush()

        false_action = AreaStep(
            area_id=area.id,
            step_type="action",
            order=3,
            service="debug",
            action="log",
            config={"message": "Odd minute"},
        )
        db_session.add(false_action)
        db_session.flush()

        # Connect steps
        trigger_step.config = {"targets": [str(condition_step.id)]}
        condition_step.config["targets"] = [str(true_action.id)]
        condition_step.config["elseBranch"] = [str(false_action.id)]
        flag_modified(condition_step, "config")
        db_session.commit()
        db_session.refresh(area)

        # Execute with odd minute (should follow else branch)
        executor = StepExecutor(db_session, area)
        trigger_data = {"minute": 43, "tick": True}
        result = executor.execute(trigger_data)

        # Verify result
        assert result["status"] == "success"
        assert result["steps_executed"] == 3
        assert result["execution_log"][1]["condition_result"] is False
        assert result["execution_log"][2]["step_id"] == str(false_action.id)

    def test_execute_workflow_prevents_infinite_loop(self, db_session: Session):
        """Test that step executor prevents infinite loops."""
        # Create area with circular reference
        user_id = uuid.uuid4()
        area = Area(
            user_id=user_id,
            name="Loop Test",
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="debug",
            reaction_action="log",
            enabled=True,
        )
        db_session.add(area)
        db_session.commit()

        # Create steps that point to each other
        step1 = AreaStep(
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="time",
            action="every_interval",
            config={},
        )
        db_session.add(step1)
        db_session.flush()

        step2 = AreaStep(
            area_id=area.id,
            step_type="action",
            order=1,
            service="debug",
            action="log",
            config={},
        )
        db_session.add(step2)
        db_session.flush()

        # Create circular reference
        step1.config = {"targets": [str(step2.id)]}
        step2.config = {"targets": [str(step1.id)]}  # Point back to step1
        db_session.commit()
        db_session.refresh(area)

        # Execute - should handle the loop gracefully
        executor = StepExecutor(db_session, area)
        trigger_data = {"tick": True}
        result = executor.execute(trigger_data)

        # Should execute step1 and step2 once, then stop
        assert result["status"] == "success"
        assert result["steps_executed"] == 2

    def test_execute_workflow_missing_handler(self, db_session: Session):
        """Test executing workflow with missing action handler."""
        # Create area
        user_id = uuid.uuid4()
        area = Area(
            user_id=user_id,
            name="Missing Handler Test",
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="debug",
            reaction_action="log",
            enabled=True,
        )
        db_session.add(area)
        db_session.commit()

        # Add step with non-existent handler
        trigger_step = AreaStep(
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="time",
            action="every_interval",
            config={},
        )
        db_session.add(trigger_step)
        db_session.flush()

        invalid_action = AreaStep(
            area_id=area.id,
            step_type="action",
            order=1,
            service="nonexistent",
            action="invalid",
            config={},
        )
        db_session.add(invalid_action)
        db_session.flush()

        trigger_step.config = {"targets": [str(invalid_action.id)]}
        db_session.commit()
        db_session.refresh(area)

        # Execute
        executor = StepExecutor(db_session, area)
        trigger_data = {"tick": True}
        result = executor.execute(trigger_data)

        # Should log failure but not crash
        assert result["status"] == "failed"
        assert result["steps_executed"] == 2
        assert result["execution_log"][1]["status"] == "failed"
        assert "no handler found" in result["execution_log"][1]["error"].lower()

    def test_execute_workflow_condition_evaluation_error(self, db_session: Session):
        """Test executing workflow with invalid condition."""
        # Create area
        user_id = uuid.uuid4()
        area = Area(
            user_id=user_id,
            name="Invalid Condition Test",
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="debug",
            reaction_action="log",
            enabled=True,
        )
        db_session.add(area)
        db_session.commit()

        # Add condition with invalid field reference
        trigger_step = AreaStep(
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="time",
            action="every_interval",
            config={},
        )
        db_session.add(trigger_step)
        db_session.flush()

        condition_step = AreaStep(
            area_id=area.id,
            step_type="condition",
            order=1,
            config={
                "conditionType": "expression",
                "expression": "trigger.nonexistent_field > 10",
            },
        )
        db_session.add(condition_step)
        db_session.flush()

        trigger_step.config = {"targets": [str(condition_step.id)]}
        db_session.commit()
        db_session.refresh(area)

        # Execute
        executor = StepExecutor(db_session, area)
        trigger_data = {"minute": 42}
        result = executor.execute(trigger_data)

        # Should log condition evaluation failure
        assert result["status"] == "failed"
        assert result["execution_log"][1]["status"] == "failed"
        assert "not found" in result["execution_log"][1]["error"].lower()


class TestExecuteAreaHelper:
    """Tests for execute_area helper function."""

    def test_execute_area_helper(self, db_session: Session):
        """Test execute_area helper function."""
        # Create simple area
        user_id = uuid.uuid4()
        area = Area(
            user_id=user_id,
            name="Helper Test Area",
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="debug",
            reaction_action="log",
            enabled=True,
        )
        db_session.add(area)
        db_session.commit()

        # Execute using helper
        trigger_data = {"now": "2024-01-01T12:00:00Z", "tick": True}
        result = execute_area(db_session, area, trigger_data)

        # Verify result
        assert result["status"] == "success"
        assert result["steps_executed"] >= 1
        assert "execution_log" in result
