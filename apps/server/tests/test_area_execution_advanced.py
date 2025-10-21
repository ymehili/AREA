"""Advanced tests for area execution engine."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import pytest
from sqlalchemy.orm import Session

from app.services.area_execution import (
    ExecutionEngine,
    execute_area_steps,
    AreaExecutionState,
)
from app.models.area import Area
from app.models.area_step import AreaStep
from app.models.user import User


class TestAreaExecutionState:
    """Test AreaExecutionState class."""

    def test_area_execution_state_initialization(self):
        """Test AreaExecutionState initialization."""
        state = AreaExecutionState("test_area_id", 0)
        
        assert state.area_id == "test_area_id"
        assert state.current_step_index == 0
        assert state.start_time is not None

    def test_area_execution_state_with_start_time(self):
        """Test AreaExecutionState with custom start time."""
        start_time = datetime.now(timezone.utc)
        state = AreaExecutionState("test_area_id", 2, start_time)
        
        assert state.area_id == "test_area_id"
        assert state.current_step_index == 2
        assert state.start_time == start_time


class TestExecutionEngine:
    """Test ExecutionEngine class."""

    @pytest.mark.asyncio
    async def test_execute_area_steps_success(self, db_session: Session):
        """Test successful execution of area steps."""
        # Create test user
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        # Create test area
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        # Create test steps
        step1 = AreaStep(
            area_id=area.id,
            order=1,
            step_type="action",
            service="gmail",
            action="send_email",
            config={"to": "recipient@example.com", "subject": "Test"}
        )
        db_session.add(step1)
        db_session.commit()
        
        engine = ExecutionEngine(db_session)
        
        # Mock the reaction handler
        with patch.object(engine.registry, "get_reaction_handler") as mock_get_handler:
            mock_handler = Mock()
            mock_get_handler.return_value = mock_handler
            
            result = await engine.execute_area_steps(area, {"test": "data"})
            
            assert result is True
            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_area_steps_no_steps(self, db_session: Session):
        """Test execution with no steps."""
        # Create test user
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        # Create test area with no steps
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        engine = ExecutionEngine(db_session)
        
        result = await engine.execute_area_steps(area, {"test": "data"})
        
        # Should return True for empty steps
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_area_steps_with_delay(self, db_session: Session):
        """Test execution with delay step."""
        # Create test user
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        # Create test area
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        # Create delay step
        step1 = AreaStep(
            area_id=area.id,
            order=1,
            step_type="delay",
            service=None,
            action=None,
            config={"duration": 1, "unit": "seconds"}
        )
        db_session.add(step1)
        db_session.commit()
        
        engine = ExecutionEngine(db_session)
        
        result = await engine.execute_area_steps(area, {"test": "data"})
        
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_area_steps_multiple_steps(self, db_session: Session):
        """Test execution with multiple steps."""
        # Create test user
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        # Create test area
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        # Create multiple steps
        step1 = AreaStep(
            area_id=area.id,
            order=1,
            step_type="action",
            service="gmail",
            action="send_email",
            config={"to": "recipient@example.com"}
        )
        step2 = AreaStep(
            area_id=area.id,
            order=2,
            step_type="delay",
            service=None,
            action=None,
            config={"duration": 1, "unit": "seconds"}
        )
        step3 = AreaStep(
            area_id=area.id,
            order=3,
            step_type="action",
            service="discord",
            action="send_message",
            config={"message": "Test"}
        )
        db_session.add_all([step1, step2, step3])
        db_session.commit()
        
        engine = ExecutionEngine(db_session)
        
        # Mock the reaction handler
        with patch.object(engine.registry, "get_reaction_handler") as mock_get_handler:
            mock_handler = Mock()
            mock_get_handler.return_value = mock_handler
            
            result = await engine.execute_area_steps(area, {"test": "data"})
            
            assert result is True
            # Should be called twice (for step1 and step3)
            assert mock_get_handler.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_area_steps_unknown_step_type(self, db_session: Session):
        """Test execution with unknown step type."""
        # Create test user
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        # Create test area
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        # Create step with unknown type
        step1 = AreaStep(
            area_id=area.id,
            order=1,
            step_type="unknown_type",
            service="gmail",
            action="send_email",
            config={}
        )
        db_session.add(step1)
        db_session.commit()
        
        engine = ExecutionEngine(db_session)
        
        result = await engine.execute_area_steps(area, {"test": "data"})
        
        # Should return False for unknown step type
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_area_steps_handler_exception(self, db_session: Session):
        """Test execution when handler raises exception."""
        # Create test user
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        # Create test area
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        # Create test step
        step1 = AreaStep(
            area_id=area.id,
            order=1,
            step_type="action",
            service="gmail",
            action="send_email",
            config={}
        )
        db_session.add(step1)
        db_session.commit()
        
        engine = ExecutionEngine(db_session)
        
        # Mock the reaction handler to raise exception
        with patch.object(engine.registry, "get_reaction_handler") as mock_get_handler:
            mock_handler = Mock(side_effect=Exception("Test error"))
            mock_get_handler.return_value = mock_handler
            
            result = await engine.execute_area_steps(area, {"test": "data"})
            
            # Should return False on exception
            assert result is False

    @pytest.mark.asyncio
    async def test_execute_delay_step_seconds(self, db_session: Session):
        """Test delay step with seconds unit."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="delay",
            config={"duration": 1, "unit": "seconds"}
        )
        
        engine = ExecutionEngine(db_session)
        
        # Should complete without error
        await engine._execute_delay_step(area, step, {})

    @pytest.mark.asyncio
    async def test_execute_delay_step_minutes(self, db_session: Session):
        """Test delay step with minutes unit."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="delay",
            config={"duration": 0.01, "unit": "minutes"}  # Small duration for testing
        )
        
        engine = ExecutionEngine(db_session)
        
        # Should complete without error
        await engine._execute_delay_step(area, step, {})

    @pytest.mark.asyncio
    async def test_execute_delay_step_hours(self, db_session: Session):
        """Test delay step with hours unit."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="delay",
            config={"duration": 0.0001, "unit": "hours"}  # Very small duration
        )
        
        engine = ExecutionEngine(db_session)
        
        # Should complete without error
        await engine._execute_delay_step(area, step, {})

    @pytest.mark.asyncio
    async def test_execute_delay_step_days(self, db_session: Session):
        """Test delay step with days unit."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="delay",
            config={"duration": 0.00001, "unit": "days"}  # Very small duration
        )
        
        engine = ExecutionEngine(db_session)
        
        # Should complete without error
        await engine._execute_delay_step(area, step, {})

    @pytest.mark.asyncio
    async def test_execute_delay_step_invalid_unit(self, db_session: Session):
        """Test delay step with invalid unit."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="delay",
            config={"duration": 1, "unit": "invalid_unit"}
        )
        
        engine = ExecutionEngine(db_session)
        
        # Should default to seconds
        await engine._execute_delay_step(area, step, {})

    @pytest.mark.asyncio
    async def test_execute_delay_step_no_config(self, db_session: Session):
        """Test delay step with no config."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="delay",
            config=None
        )
        
        engine = ExecutionEngine(db_session)
        
        # Should use default
        await engine._execute_delay_step(area, step, {})

    @pytest.mark.asyncio
    async def test_execute_delay_step_wrong_type(self, db_session: Session):
        """Test delay step execution with wrong step type."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="action",  # Wrong type
            config={}
        )
        
        engine = ExecutionEngine(db_session)
        
        with pytest.raises(ValueError):
            await engine._execute_delay_step(area, step, {})

    @pytest.mark.asyncio
    async def test_execute_action_reaction_step_missing_handler(self, db_session: Session):
        """Test action/reaction step when handler is missing."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="action",
            service="unknown_service",
            action="unknown_action",
            config={}
        )
        
        engine = ExecutionEngine(db_session)
        
        with patch.object(engine.registry, "get_reaction_handler") as mock_get_handler:
            mock_get_handler.return_value = None
            
            with pytest.raises(ValueError):
                await engine._execute_action_reaction_step(area, step, {})

    @pytest.mark.asyncio
    async def test_execute_action_reaction_step_missing_service(self, db_session: Session):
        """Test action/reaction step with missing service."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="action",
            service=None,
            action="send_email",
            config={}
        )
        
        engine = ExecutionEngine(db_session)
        
        with pytest.raises(ValueError):
            await engine._execute_action_reaction_step(area, step, {})

    @pytest.mark.asyncio
    async def test_execute_action_reaction_step_wrong_type(self, db_session: Session):
        """Test action/reaction step execution with wrong step type."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="delay",  # Wrong type
            service="gmail",
            action="send_email",
            config={}
        )
        
        engine = ExecutionEngine(db_session)
        
        with pytest.raises(ValueError):
            await engine._execute_action_reaction_step(area, step, {})

    @pytest.mark.asyncio
    async def test_execute_area_steps_condition_step(self, db_session: Session):
        """Test execution with condition step (not yet implemented)."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="condition",
            service="gmail",
            action="check_condition",
            config={}
        )
        db_session.add(step)
        db_session.commit()
        
        engine = ExecutionEngine(db_session)
        
        # Should log but continue
        result = await engine.execute_area_steps(area, {})
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_area_steps_trigger_step(self, db_session: Session):
        """Test execution with trigger step (not yet implemented)."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        step = AreaStep(
            area_id=area.id,
            order=1,
            step_type="trigger",
            service="gmail",
            action="new_email",
            config={}
        )
        db_session.add(step)
        db_session.commit()
        
        engine = ExecutionEngine(db_session)
        
        # Should log but continue
        result = await engine.execute_area_steps(area, {})
        assert result is True


class TestExecuteAreaStepsFunction:
    """Test the public execute_area_steps function."""

    @pytest.mark.asyncio
    async def test_execute_area_steps_function(self, db_session: Session):
        """Test the public execute_area_steps function."""
        user = User(email="test@example.com", hashed_password="test", is_confirmed=True)
        db_session.add(user)
        db_session.commit()
        
        area = Area(
            user_id=user.id,
            name="Test Area",
            enabled=True,
            trigger_service="time",
            trigger_action="every_interval",
            reaction_service="gmail",
            reaction_action="send_email",
        )
        db_session.add(area)
        db_session.commit()
        
        result = await execute_area_steps(db_session, area, {"test": "data"})
        
        # Should return True for area with no steps
        assert result is True
