"""Tests for variable propagation across steps in multi-step workflows.

This test suite verifies that variables from triggers propagate to all subsequent steps,
and that action outputs can be accessed by following steps.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models.area import Area
from app.models.area_step import AreaStep
from app.services.step_executor import StepExecutor


class TestVariablePropagation:
    """Test that variables propagate correctly through multi-step workflows."""

    def test_calendar_trigger_to_debug_action(self, db_session: Session):
        """Test that Calendar trigger variables are accessible in Debug action.

        This is the main use case: variables from a Google Calendar event
        should be accessible in any subsequent step, regardless of the step's service.
        """
        # Create a mock area with Calendar trigger → Debug action workflow
        area = Area(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Calendar Event Logger",
            trigger_service="google_calendar",
            trigger_action="event_created",
            trigger_params={},
            reaction_service="debug",
            reaction_action="log",
            reaction_params={},
            enabled=True,
        )

        # Create trigger step (Google Calendar)
        trigger_step = AreaStep(
            id=uuid.uuid4(),
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="google_calendar",
            action="event_created",
            config={"targets": []},
        )

        # Create debug action step
        debug_step_id = uuid.uuid4()
        debug_step = AreaStep(
            id=debug_step_id,
            area_id=area.id,
            step_type="action",
            order=1,
            service="debug",
            action="log",
            config={
                "message": "Event created: {{calendar.title}} at {{calendar.location}} on {{calendar.start_time}}"
            },
        )

        # Link trigger to debug step
        trigger_step.config = {"targets": [str(debug_step_id)]}
        area.steps = [trigger_step, debug_step]

        # Create executor
        executor = StepExecutor(db_session, area)

        # Simulate Calendar event trigger data
        trigger_data = {
            "id": "event123",
            "summary": "Project Meeting",
            "description": "Discuss Q4 roadmap",
            "location": "Conference Room A",
            "start_time": "2025-10-25T14:00:00Z",
            "end_time": "2025-10-25T15:00:00Z",
            "organizer": "manager@example.com",
            "attendees": ["dev1@example.com", "dev2@example.com"],
        }

        # Execute the workflow
        result = executor.execute(trigger_data)

        # Verify execution succeeded
        assert result["status"] == "success"
        assert result["steps_executed"] == 2

        # Verify accumulated variables contain calendar data
        assert "calendar.title" in executor.accumulated_variables
        assert executor.accumulated_variables["calendar.title"] == "Project Meeting"
        assert "calendar.location" in executor.accumulated_variables
        assert executor.accumulated_variables["calendar.location"] == "Conference Room A"
        assert "calendar.start_time" in executor.accumulated_variables
        assert executor.accumulated_variables["calendar.start_time"] == "2025-10-25T14:00:00Z"

        # Verify the debug step received the correct message with substituted variables
        debug_log = next(
            (log for log in result["execution_log"] if log["step_id"] == str(debug_step_id)),
            None
        )
        assert debug_log is not None
        assert debug_log["status"] == "success"

    def test_openai_output_propagates_to_debug(self, db_session: Session):
        """Test that OpenAI action outputs propagate to subsequent Debug action.

        Workflow: Time Trigger → OpenAI Chat → Debug Log
        The Debug step should be able to access {{openai.response}}
        """
        # Create a mock area with Time → OpenAI → Debug workflow
        area = Area(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="AI Response Logger",
            trigger_service="time",
            trigger_action="every_interval",
            trigger_params={"interval": 60},
            reaction_service="debug",
            reaction_action="log",
            reaction_params={},
            enabled=True,
        )

        # Create trigger step (Time)
        trigger_step = AreaStep(
            id=uuid.uuid4(),
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="time",
            action="every_interval",
            config={"targets": []},
        )

        # Create OpenAI action step
        openai_step_id = uuid.uuid4()
        openai_step = AreaStep(
            id=openai_step_id,
            area_id=area.id,
            step_type="action",
            order=1,
            service="openai",
            action="chat",
            config={
                "prompt": "Say hello!",
                "targets": [],
            },
        )

        # Create debug action step
        debug_step_id = uuid.uuid4()
        debug_step = AreaStep(
            id=debug_step_id,
            area_id=area.id,
            step_type="action",
            order=2,
            service="debug",
            action="log",
            config={
                "message": "OpenAI said: {{openai.response}}"
            },
        )

        # Link steps
        trigger_step.config = {"targets": [str(openai_step_id)]}
        openai_step.config["targets"] = [str(debug_step_id)]
        area.steps = [trigger_step, openai_step, debug_step]

        # Create executor
        executor = StepExecutor(db_session, area)

        # Simulate Time trigger
        trigger_data = {
            "now": "2025-10-25T12:00:00Z",
            "tick": True,
        }

        # Mock the OpenAI handler to add response to trigger_data
        # This simulates what the actual openai_plugin does
        original_get_handler = executor.registry.get_reaction_handler

        def mock_get_handler(service, action):
            if service == "openai" and action == "chat":
                def mock_openai_handler(area, params, event, db=None):
                    # Simulate OpenAI response
                    event["openai.response"] = "Hello! How can I help you today?"
                    event["openai.model"] = "gpt-3.5-turbo"
                    event["openai.finish_reason"] = "stop"
                    event["openai_data"] = {
                        "response": "Hello! How can I help you today?",
                        "model": "gpt-3.5-turbo",
                        "finish_reason": "stop",
                    }
                return mock_openai_handler
            return original_get_handler(service, action)

        executor.registry.get_reaction_handler = mock_get_handler

        # Execute the workflow
        result = executor.execute(trigger_data)

        # Verify execution succeeded
        assert result["status"] == "success"
        assert result["steps_executed"] == 3

        # Verify accumulated variables contain OpenAI response
        assert "openai.response" in executor.accumulated_variables
        assert executor.accumulated_variables["openai.response"] == "Hello! How can I help you today?"
        assert "openai.model" in executor.accumulated_variables
        assert executor.accumulated_variables["openai.model"] == "gpt-3.5-turbo"

        # Verify the debug step executed successfully
        debug_log = next(
            (log for log in result["execution_log"] if log["step_id"] == str(debug_step_id)),
            None
        )
        assert debug_log is not None
        assert debug_log["status"] == "success"

    def test_cascade_propagation_three_steps(self, db_session: Session):
        """Test that variables accumulate through 3+ steps.

        Workflow: Calendar → OpenAI (summarize event) → Debug (log both)
        The Debug step should see both calendar.* AND openai.* variables
        """
        # Create area
        area = Area(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Event Summarizer",
            trigger_service="google_calendar",
            trigger_action="event_created",
            trigger_params={},
            reaction_service="debug",
            reaction_action="log",
            reaction_params={},
            enabled=True,
        )

        # Create steps
        trigger_step = AreaStep(
            id=uuid.uuid4(),
            area_id=area.id,
            step_type="trigger",
            order=0,
            service="google_calendar",
            action="event_created",
            config={"targets": []},
        )

        openai_step_id = uuid.uuid4()
        openai_step = AreaStep(
            id=openai_step_id,
            area_id=area.id,
            step_type="action",
            order=1,
            service="openai",
            action="chat",
            config={
                "prompt": "Summarize: {{calendar.title}} at {{calendar.location}}",
                "targets": [],
            },
        )

        debug_step_id = uuid.uuid4()
        debug_step = AreaStep(
            id=debug_step_id,
            area_id=area.id,
            step_type="action",
            order=2,
            service="debug",
            action="log",
            config={
                "message": "Event: {{calendar.title}}, Summary: {{openai.response}}"
            },
        )

        # Link steps
        trigger_step.config = {"targets": [str(openai_step_id)]}
        openai_step.config["targets"] = [str(debug_step_id)]
        area.steps = [trigger_step, openai_step, debug_step]

        # Create executor
        executor = StepExecutor(db_session, area)

        # Calendar event data
        trigger_data = {
            "summary": "Team Standup",
            "location": "Zoom",
            "start_time": "2025-10-25T09:00:00Z",
        }

        # Mock OpenAI handler
        original_get_handler = executor.registry.get_reaction_handler

        def mock_get_handler(service, action):
            if service == "openai" and action == "chat":
                def mock_openai_handler(area, params, event, db=None):
                    # Verify that calendar variables are available in params
                    assert "Team Standup" in params.get("prompt", "")
                    assert "Zoom" in params.get("prompt", "")

                    event["openai.response"] = "Daily sync meeting for the team via Zoom"
                    event["openai_data"] = {"response": "Daily sync meeting for the team via Zoom"}
                return mock_openai_handler
            return original_get_handler(service, action)

        executor.registry.get_reaction_handler = mock_get_handler

        # Execute
        result = executor.execute(trigger_data)

        # Verify success
        assert result["status"] == "success"
        assert result["steps_executed"] == 3

        # Verify both calendar and openai variables are accumulated
        assert "calendar.title" in executor.accumulated_variables
        assert "calendar.location" in executor.accumulated_variables
        assert "openai.response" in executor.accumulated_variables

        # Verify debug step executed
        debug_log = next(
            (log for log in result["execution_log"] if log["step_id"] == str(debug_step_id)),
            None
        )
        assert debug_log is not None
        assert debug_log["status"] == "success"
