"""Tests for condition evaluator service."""

from __future__ import annotations

import pytest

from app.services.condition_evaluator import (
    ConditionEvaluationError,
    ConditionEvaluator,
    UnsafeExpressionError,
    evaluate_condition,
)


class TestConditionEvaluator:
    """Tests for ConditionEvaluator class."""

    def test_simple_condition_eq(self):
        """Test simple equality condition."""
        context = {"trigger": {"subject": "Invoice"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_simple_condition(
            "trigger.subject", "eq", "Invoice"
        )
        assert result is True

        result = evaluator.evaluate_simple_condition(
            "trigger.subject", "eq", "Payment"
        )
        assert result is False

    def test_simple_condition_ne(self):
        """Test simple not-equal condition."""
        context = {"trigger": {"status": "active"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_simple_condition(
            "trigger.status", "ne", "inactive"
        )
        assert result is True

        result = evaluator.evaluate_simple_condition(
            "trigger.status", "ne", "active"
        )
        assert result is False

    def test_simple_condition_numeric_comparison(self):
        """Test numeric comparison conditions."""
        context = {"trigger": {"amount": 150, "count": 5}}
        evaluator = ConditionEvaluator(context)

        # Greater than
        assert evaluator.evaluate_simple_condition("trigger.amount", "gt", 100) is True
        assert evaluator.evaluate_simple_condition("trigger.amount", "gt", 200) is False

        # Less than
        assert evaluator.evaluate_simple_condition("trigger.count", "lt", 10) is True
        assert evaluator.evaluate_simple_condition("trigger.count", "lt", 3) is False

        # Greater than or equal
        assert evaluator.evaluate_simple_condition("trigger.amount", "gte", 150) is True
        assert evaluator.evaluate_simple_condition("trigger.amount", "gte", 151) is False

        # Less than or equal
        assert evaluator.evaluate_simple_condition("trigger.count", "lte", 5) is True
        assert evaluator.evaluate_simple_condition("trigger.count", "lte", 4) is False

    def test_simple_condition_string_operations(self):
        """Test string operation conditions."""
        context = {"trigger": {"subject": "Invoice from Acme Corp"}}
        evaluator = ConditionEvaluator(context)

        # Contains
        assert (
            evaluator.evaluate_simple_condition(
                "trigger.subject", "contains", "Invoice"
            )
            is True
        )
        assert (
            evaluator.evaluate_simple_condition(
                "trigger.subject", "contains", "Payment"
            )
            is False
        )

        # Startswith
        assert (
            evaluator.evaluate_simple_condition(
                "trigger.subject", "startswith", "Invoice"
            )
            is True
        )
        assert (
            evaluator.evaluate_simple_condition(
                "trigger.subject", "startswith", "Payment"
            )
            is False
        )

        # Endswith
        assert (
            evaluator.evaluate_simple_condition(
                "trigger.subject", "endswith", "Corp"
            )
            is True
        )
        assert (
            evaluator.evaluate_simple_condition(
                "trigger.subject", "endswith", "Inc"
            )
            is False
        )

    def test_simple_condition_nested_field(self):
        """Test condition with nested field path."""
        context = {
            "trigger": {
                "email": {"sender": "user@example.com", "subject": "Test"}
            }
        }
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_simple_condition(
            "trigger.email.sender", "eq", "user@example.com"
        )
        assert result is True

    def test_simple_condition_field_not_found(self):
        """Test condition with non-existent field."""
        context = {"trigger": {"subject": "Test"}}
        evaluator = ConditionEvaluator(context)

        with pytest.raises(ConditionEvaluationError) as exc_info:
            evaluator.evaluate_simple_condition("trigger.nonexistent", "eq", "value")

        assert "not found" in str(exc_info.value).lower()

    def test_simple_condition_unknown_operator(self):
        """Test condition with unknown operator."""
        context = {"trigger": {"value": 10}}
        evaluator = ConditionEvaluator(context)

        with pytest.raises(ConditionEvaluationError) as exc_info:
            evaluator.evaluate_simple_condition("trigger.value", "unknown_op", 10)

        assert "unknown operator" in str(exc_info.value).lower()

    def test_expression_simple_comparison(self):
        """Test expression with simple comparison."""
        context = {"trigger": {"amount": 150}}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate_expression("trigger.amount > 100") is True
        assert evaluator.evaluate_expression("trigger.amount < 100") is False
        assert evaluator.evaluate_expression("trigger.amount == 150") is True
        assert evaluator.evaluate_expression("trigger.amount != 200") is True

    def test_expression_logical_and(self):
        """Test expression with AND logic."""
        context = {"trigger": {"amount": 150, "status": "pending"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_expression(
            'trigger.amount > 100 and trigger.status == "pending"'
        )
        assert result is True

        result = evaluator.evaluate_expression(
            'trigger.amount > 200 and trigger.status == "pending"'
        )
        assert result is False

    def test_expression_logical_or(self):
        """Test expression with OR logic."""
        context = {"trigger": {"amount": 50, "priority": "high"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_expression(
            'trigger.amount > 100 or trigger.priority == "high"'
        )
        assert result is True

        result = evaluator.evaluate_expression(
            'trigger.amount > 100 or trigger.priority == "low"'
        )
        assert result is False

    def test_expression_logical_not(self):
        """Test expression with NOT logic."""
        context = {"trigger": {"active": False}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_expression("not trigger.active")
        assert result is True

        context = {"trigger": {"active": True}}
        evaluator = ConditionEvaluator(context)
        result = evaluator.evaluate_expression("not trigger.active")
        assert result is False

    def test_expression_complex_logic(self):
        """Test expression with complex logic combinations."""
        context = {
            "trigger": {
                "amount": 150,
                "status": "pending",
                "priority": "high",
            }
        }
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_expression(
            '(trigger.amount > 100 and trigger.status == "pending") or trigger.priority == "urgent"'
        )
        assert result is True

    def test_expression_with_constants(self):
        """Test expression with various constant types."""
        context = {"trigger": {"count": 5, "enabled": True, "name": "test"}}
        evaluator = ConditionEvaluator(context)

        # Integer
        assert evaluator.evaluate_expression("trigger.count == 5") is True

        # Boolean
        assert evaluator.evaluate_expression("trigger.enabled == True") is True

        # String
        assert evaluator.evaluate_expression('trigger.name == "test"') is True

    def test_expression_arithmetic(self):
        """Test expression with arithmetic operations."""
        context = {"trigger": {"price": 100, "quantity": 3}}
        evaluator = ConditionEvaluator(context)

        # Multiplication
        result = evaluator.evaluate_expression(
            "trigger.price * trigger.quantity > 250"
        )
        assert result is True

        # Addition
        result = evaluator.evaluate_expression("trigger.price + trigger.quantity == 103")
        assert result is True

    def test_expression_field_not_found(self):
        """Test expression with non-existent field."""
        context = {"trigger": {"value": 10}}
        evaluator = ConditionEvaluator(context)

        with pytest.raises(ConditionEvaluationError) as exc_info:
            evaluator.evaluate_expression("trigger.nonexistent > 5")

        assert "not found" in str(exc_info.value).lower()

    def test_expression_unsafe_import(self):
        """Test that unsafe expressions are rejected."""
        context = {"trigger": {"value": 10}}
        evaluator = ConditionEvaluator(context)

        with pytest.raises(UnsafeExpressionError):
            evaluator.evaluate_expression("__import__('os').system('ls')")

    def test_expression_unsafe_function_call(self):
        """Test that unsafe function calls are rejected."""
        context = {"trigger": {"value": 10}}
        evaluator = ConditionEvaluator(context)

        with pytest.raises(UnsafeExpressionError):
            evaluator.evaluate_expression("eval('1+1')")

    def test_expression_safe_string_methods(self):
        """Test that safe string methods are allowed."""
        context = {"trigger": {"text": "Hello World"}}
        evaluator = ConditionEvaluator(context)

        # These should work (safe methods)
        result = evaluator.evaluate_expression('trigger.text.lower() == "hello world"')
        assert result is True

        result = evaluator.evaluate_expression('trigger.text.upper() == "HELLO WORLD"')
        assert result is True

    def test_resolve_field_nested(self):
        """Test resolving deeply nested field paths."""
        context = {
            "trigger": {
                "data": {
                    "user": {
                        "profile": {"name": "John Doe"}
                    }
                }
            }
        }
        evaluator = ConditionEvaluator(context)

        value = evaluator._resolve_field("trigger.data.user.profile.name")
        assert value == "John Doe"

    def test_time_based_condition(self):
        """Test condition based on time values (for our test case)."""
        # Simulate minute being even
        context = {"trigger": {"minute": 42}}
        evaluator = ConditionEvaluator(context)

        # Minute is even (using modulo)
        result = evaluator.evaluate_expression("trigger.minute % 2 == 0")
        assert result is True

        # Minute is odd
        context = {"trigger": {"minute": 43}}
        evaluator = ConditionEvaluator(context)
        result = evaluator.evaluate_expression("trigger.minute % 2 == 0")
        assert result is False


class TestEvaluateConditionHelper:
    """Tests for evaluate_condition helper function."""

    def test_evaluate_simple_condition_config(self):
        """Test evaluating simple condition from config."""
        config = {
            "conditionType": "simple",
            "simple": {
                "field": "trigger.subject",
                "operator": "contains",
                "value": "Invoice",
            },
        }
        context = {"trigger": {"subject": "Invoice #1234"}}

        result = evaluate_condition(config, context)
        assert result is True

    def test_evaluate_expression_condition_config(self):
        """Test evaluating expression condition from config."""
        config = {
            "conditionType": "expression",
            "expression": "trigger.amount > 100 and trigger.status == 'pending'",
        }
        context = {"trigger": {"amount": 150, "status": "pending"}}

        result = evaluate_condition(config, context)
        assert result is True

    def test_evaluate_condition_missing_type(self):
        """Test that missing condition type defaults to simple."""
        config = {
            "simple": {
                "field": "trigger.value",
                "operator": "eq",
                "value": 10,
            }
        }
        context = {"trigger": {"value": 10}}

        result = evaluate_condition(config, context)
        assert result is True

    def test_evaluate_condition_missing_simple_config(self):
        """Test error when simple config is missing."""
        config = {"conditionType": "simple"}
        context = {"trigger": {}}

        with pytest.raises(ConditionEvaluationError) as exc_info:
            evaluate_condition(config, context)

        assert "simple condition configuration missing" in str(exc_info.value).lower()

    def test_evaluate_condition_missing_expression(self):
        """Test error when expression is missing."""
        config = {"conditionType": "expression"}
        context = {"trigger": {}}

        with pytest.raises(ConditionEvaluationError) as exc_info:
            evaluate_condition(config, context)

        assert "expression" in str(exc_info.value).lower()

    def test_evaluate_condition_unknown_type(self):
        """Test error with unknown condition type."""
        config = {"conditionType": "unknown"}
        context = {"trigger": {}}

        with pytest.raises(ConditionEvaluationError) as exc_info:
            evaluate_condition(config, context)

        assert "unknown condition type" in str(exc_info.value).lower()

    def test_evaluate_minute_even_condition(self):
        """Test the specific condition for our test area: minute is even."""
        config = {
            "conditionType": "expression",
            "expression": "trigger.minute % 2 == 0",
        }

        # Even minute
        context = {"trigger": {"minute": 42}}
        result = evaluate_condition(config, context)
        assert result is True

        # Odd minute
        context = {"trigger": {"minute": 43}}
        result = evaluate_condition(config, context)
        assert result is False
