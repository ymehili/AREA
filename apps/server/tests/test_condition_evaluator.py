"""Tests for condition evaluator service."""

import pytest
from app.services.condition_evaluator import (
    ConditionEvaluator,
    ConditionEvaluationError,
    UnsafeExpressionError,
    evaluate_condition,
)


class TestConditionEvaluator:
    """Test condition evaluator functionality."""

    def test_simple_condition_eq(self):
        """Test simple equality condition."""
        context = {"trigger": {"subject": "Invoice"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_simple_condition("trigger.subject", "eq", "Invoice")

        assert result is True

    def test_simple_condition_ne(self):
        """Test simple inequality condition."""
        context = {"trigger": {"subject": "Invoice"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_simple_condition("trigger.subject", "ne", "Receipt")

        assert result is True

    def test_simple_condition_gt(self):
        """Test simple greater than condition."""
        context = {"trigger": {"amount": 150}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_simple_condition("trigger.amount", "gt", 100)

        assert result is True

    def test_simple_condition_lt(self):
        """Test simple less than condition."""
        context = {"trigger": {"amount": 50}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_simple_condition("trigger.amount", "lt", 100)

        assert result is True

    def test_simple_condition_gte(self):
        """Test simple greater than or equal condition."""
        context = {"trigger": {"amount": 100}}
        evaluator = ConditionEvaluator(context)

        # Test with equal value
        result = evaluator.evaluate_simple_condition("trigger.amount", "gte", 100)
        assert result is True

        # Test with smaller value
        result = evaluator.evaluate_simple_condition("trigger.amount", "gte", 50)
        assert result is True

    def test_simple_condition_lte(self):
        """Test simple less than or equal condition."""
        context = {"trigger": {"amount": 100}}
        evaluator = ConditionEvaluator(context)

        # Test with equal value
        result = evaluator.evaluate_simple_condition("trigger.amount", "lte", 100)
        assert result is True

        # Test with larger value
        result = evaluator.evaluate_simple_condition("trigger.amount", "lte", 150)
        assert result is True

    def test_simple_condition_contains(self):
        """Test simple contains condition."""
        context = {"trigger": {"subject": "Monthly Invoice"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_simple_condition("trigger.subject", "contains", "Invoice")

        assert result is True

    def test_simple_condition_startswith(self):
        """Test simple startswith condition."""
        context = {"trigger": {"subject": "Invoice #12345"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_simple_condition("trigger.subject", "startswith", "Invoice")

        assert result is True

    def test_simple_condition_endswith(self):
        """Test simple endswith condition."""
        context = {"trigger": {"subject": "Payment Confirmation"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_simple_condition("trigger.subject", "endswith", "Confirmation")

        assert result is True

    def test_simple_condition_invalid_field(self):
        """Test simple condition with invalid field path."""
        context = {"trigger": {"subject": "Invoice"}}
        evaluator = ConditionEvaluator(context)

        with pytest.raises(ConditionEvaluationError):
            evaluator.evaluate_simple_condition("trigger.invalid_field", "eq", "value")

    def test_simple_condition_unknown_operator(self):
        """Test simple condition with unknown operator."""
        context = {"trigger": {"subject": "Invoice"}}
        evaluator = ConditionEvaluator(context)

        with pytest.raises(ConditionEvaluationError):
            evaluator.evaluate_simple_condition("trigger.subject", "unknown_op", "value")

    def test_expression_simple_comparison(self):
        """Test evaluating a simple expression with comparison."""
        context = {"trigger": {"amount": 150}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_expression("trigger.amount > 100")

        assert result is True

    def test_expression_logical_and(self):
        """Test evaluating an expression with logical AND."""
        context = {"trigger": {"amount": 150, "status": "pending"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_expression("trigger.amount > 100 and trigger.status == 'pending'")

        assert result is True

    def test_expression_logical_or(self):
        """Test evaluating an expression with logical OR."""
        context = {"trigger": {"amount": 50, "status": "approved"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_expression("trigger.amount > 100 or trigger.status == 'approved'")

        assert result is True

    def test_expression_logical_not(self):
        """Test evaluating an expression with logical NOT."""
        context = {"trigger": {"status": "pending"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_expression("not trigger.status == 'approved'")

        assert result is True

    def test_expression_complex_expression(self):
        """Test evaluating a complex expression."""
        context = {"trigger": {"amount": 150, "status": "pending", "category": "urgent"}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_expression(
            "(trigger.amount > 100 and trigger.status == 'pending') or trigger.category == 'urgent'"
        )

        assert result is True

    def test_expression_with_arithmetic(self):
        """Test evaluating an expression with arithmetic operations."""
        context = {"trigger": {"price": 100, "tax": 10}}
        evaluator = ConditionEvaluator(context)

        result = evaluator.evaluate_expression("trigger.price + trigger.tax > 105")

        assert result is True

    def test_expression_unsafe_operation(self):
        """Test that unsafe operations are rejected."""
        evaluator = ConditionEvaluator({})

        with pytest.raises(UnsafeExpressionError):
            # This should fail because function calls are not allowed
            evaluator.evaluate_expression("len('hello')")

    def test_expression_unsafe_attribute_access(self):
        """Test that unsafe attribute access is rejected."""
        context = {"trigger": {"test": "value"}}
        
        evaluator = ConditionEvaluator(context)

        with pytest.raises(UnsafeExpressionError):
            # This should fail because accessing __class__ is not allowed in the AST validation
            evaluator.evaluate_expression("trigger.__class__")

    def test_resolve_field_simple_path(self):
        """Test resolving a simple field path."""
        context = {"user": {"name": "Alice", "age": 30}}
        evaluator = ConditionEvaluator(context)

        result = evaluator._resolve_field("user.name")

        assert result == "Alice"

    def test_resolve_field_nested_path(self):
        """Test resolving a nested field path."""
        context = {"data": {"user": {"profile": {"email": "alice@example.com"}}}}
        evaluator = ConditionEvaluator(context)

        result = evaluator._resolve_field("data.user.profile.email")

        assert result == "alice@example.com"

    def test_resolve_field_invalid_path(self):
        """Test resolving an invalid field path."""
        context = {"user": {"name": "Alice"}}
        evaluator = ConditionEvaluator(context)

        with pytest.raises(ConditionEvaluationError):
            evaluator._resolve_field("user.invalid_field")

    def test_validate_ast_safe_expression(self):
        """Test that safe expressions pass validation."""
        context = {"trigger": {"amount": 150}}
        evaluator = ConditionEvaluator(context)

        # This should not raise an exception
        result = evaluator.evaluate_expression("trigger.amount > 100")
        assert result is True

    def test_eval_node_constant(self):
        """Test evaluating a constant node."""
        evaluator = ConditionEvaluator({})
        
        # This test is more of a coverage test since _eval_node is private
        # We'll test it indirectly through evaluate_expression
        result = evaluator.evaluate_expression("42")
        assert result is True  # The result gets converted to boolean in evaluate_expression

    def test_eval_node_name(self):
        """Test evaluating a name node."""
        context = {"x": 10}
        evaluator = ConditionEvaluator(context)
        
        result = evaluator.evaluate_expression("x")
        assert result is True  # The result gets converted to boolean in evaluate_expression

    def test_evaluate_condition_simple_type(self):
        """Test evaluating a condition with simple type."""
        condition_config = {
            "conditionType": "simple",
            "simple": {
                "field": "trigger.status",
                "operator": "eq",
                "value": "pending"
            }
        }
        context = {"trigger": {"status": "pending"}}

        result = evaluate_condition(condition_config, context)

        assert result is True

    def test_evaluate_condition_expression_type(self):
        """Test evaluating a condition with expression type."""
        condition_config = {
            "conditionType": "expression",
            "expression": "trigger.amount > 100"
        }
        context = {"trigger": {"amount": 150}}

        result = evaluate_condition(condition_config, context)

        assert result is True

    def test_evaluate_condition_invalid_type(self):
        """Test evaluating a condition with invalid type."""
        condition_config = {
            "conditionType": "invalid_type"
        }
        context = {}

        with pytest.raises(ConditionEvaluationError):
            evaluate_condition(condition_config, context)

    def test_evaluate_condition_missing_config(self):
        """Test evaluating a simple condition with missing configuration."""
        condition_config = {
            "conditionType": "simple"
            # Missing 'simple' configuration
        }
        context = {}

        with pytest.raises(ConditionEvaluationError):
            evaluate_condition(condition_config, context)

    def test_evaluate_condition_missing_expression(self):
        """Test evaluating an expression condition with missing expression."""
        condition_config = {
            "conditionType": "expression"
            # Missing 'expression' field
        }
        context = {}

        with pytest.raises(ConditionEvaluationError):
            evaluate_condition(condition_config, context)

    def test_evaluate_condition_missing_simple_parts(self):
        """Test evaluating a simple condition with missing parts."""
        condition_config = {
            "conditionType": "simple",
            "simple": {
                # Missing field and operator
                "value": "test"
            }
        }
        context = {}

        with pytest.raises(ConditionEvaluationError):
            evaluate_condition(condition_config, context)

    def test_expression_with_string_methods(self):
        """Test evaluating an expression with allowed string methods."""
        context = {"trigger": {"subject": "  HELLO  "}}
        evaluator = ConditionEvaluator(context)

        # Testing the allowed string methods
        result = evaluator.evaluate_expression("trigger.subject.strip().lower() == 'hello'")
        assert result is True

    def test_expression_with_unsafe_method_call(self):
        """Test that unsafe method calls are rejected."""
        evaluator = ConditionEvaluator({"x": "test"})

        with pytest.raises(UnsafeExpressionError):
            # This should fail because eval() or other unsafe methods are not allowed
            evaluator.evaluate_expression("x.eval()")