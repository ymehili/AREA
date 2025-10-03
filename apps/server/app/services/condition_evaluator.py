"""Safe condition evaluator for AREA automation conditions.

This module provides a secure expression evaluation system that supports:
- Simple comparisons: ==, !=, >, <, >=, <=
- String operations: contains, startswith, endswith
- Logical operators: and, or, not
- Variable substitution from execution context

Security: Uses AST parsing instead of eval() to prevent code injection.
"""

from __future__ import annotations

import ast
import logging
import operator
from typing import Any, Dict

logger = logging.getLogger("area")


class ConditionEvaluationError(Exception):
    """Raised when a condition cannot be evaluated."""

    pass


class UnsafeExpressionError(Exception):
    """Raised when an expression contains unsafe operations."""

    pass


# Allowed operators for safe evaluation
SAFE_OPERATORS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: operator.and_,
    ast.Or: operator.or_,
    ast.Not: operator.not_,
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}


class ConditionEvaluator:
    """Safe evaluator for condition expressions."""

    def __init__(self, context: Dict[str, Any]) -> None:
        """Initialize evaluator with execution context.

        Args:
            context: Dictionary containing variables available for evaluation
                    (e.g., {"trigger": {"subject": "Invoice"}, "now": {...}})
        """
        self.context = context

    def evaluate_simple_condition(
        self,
        field: str,
        operator_name: str,
        value: Any,
    ) -> bool:
        """Evaluate a simple condition with field-operator-value pattern.

        Args:
            field: Field path to evaluate (e.g., "trigger.subject")
            operator_name: Operator name (eq, ne, gt, lt, gte, lte, contains, startswith, endswith)
            value: Value to compare against

        Returns:
            Boolean result of the condition evaluation

        Raises:
            ConditionEvaluationError: If evaluation fails
        """
        try:
            # Resolve field value from context
            field_value = self._resolve_field(field)

            # Evaluate based on operator
            if operator_name == "eq":
                return field_value == value
            elif operator_name == "ne":
                return field_value != value
            elif operator_name == "gt":
                return field_value > value
            elif operator_name == "lt":
                return field_value < value
            elif operator_name == "gte":
                return field_value >= value
            elif operator_name == "lte":
                return field_value <= value
            elif operator_name == "contains":
                return str(value) in str(field_value)
            elif operator_name == "startswith":
                return str(field_value).startswith(str(value))
            elif operator_name == "endswith":
                return str(field_value).endswith(str(value))
            else:
                raise ConditionEvaluationError(
                    f"Unknown operator: {operator_name}"
                )
        except Exception as e:
            logger.error(
                "Error evaluating simple condition",
                extra={
                    "field": field,
                    "operator": operator_name,
                    "value": value,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise ConditionEvaluationError(
                f"Failed to evaluate condition: {e}"
            ) from e

    def evaluate_expression(self, expression: str) -> bool:
        """Evaluate a complex expression safely.

        Args:
            expression: Python-like expression to evaluate
                       (e.g., "trigger.amount > 100 and trigger.status == 'pending'")

        Returns:
            Boolean result of the expression evaluation

        Raises:
            UnsafeExpressionError: If expression contains unsafe operations
            ConditionEvaluationError: If evaluation fails
        """
        try:
            # Parse the expression into an AST
            tree = ast.parse(expression, mode="eval")

            # Validate the AST for safety
            self._validate_ast(tree)

            # Evaluate the AST
            result = self._eval_node(tree.body)

            # Ensure result is boolean
            return bool(result)

        except (UnsafeExpressionError, ConditionEvaluationError):
            raise
        except Exception as e:
            logger.error(
                "Error evaluating expression",
                extra={"expression": expression, "error": str(e)},
                exc_info=True,
            )
            raise ConditionEvaluationError(
                f"Failed to evaluate expression: {e}"
            ) from e

    def _resolve_field(self, field_path: str) -> Any:
        """Resolve a dotted field path from context.

        Args:
            field_path: Dot-separated path (e.g., "trigger.subject")

        Returns:
            Value at the field path

        Raises:
            ConditionEvaluationError: If field path cannot be resolved
        """
        parts = field_path.split(".")
        value = self.context

        for part in parts:
            if isinstance(value, dict):
                if part not in value:
                    raise ConditionEvaluationError(
                        f"Field '{part}' not found in context path '{field_path}'"
                    )
                value = value[part]
            else:
                # Try to access as attribute
                if not hasattr(value, part):
                    raise ConditionEvaluationError(
                        f"Field '{part}' not found in context path '{field_path}'"
                    )
                value = getattr(value, part)

        return value

    def _validate_ast(self, tree: ast.AST) -> None:
        """Validate that AST only contains safe operations.

        Args:
            tree: AST to validate

        Raises:
            UnsafeExpressionError: If AST contains unsafe operations
        """
        # Build list of allowed node types
        allowed_nodes = [
            ast.Expression,
            ast.Load,
            ast.Store,
            ast.Constant,
            ast.Name,
            ast.Attribute,
            ast.Compare,
            ast.BoolOp,
            ast.UnaryOp,
            ast.BinOp,
            ast.Call,
            # Comparison operators
            ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
            # Boolean operators
            ast.And, ast.Or, ast.Not,
            # Arithmetic operators
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
        ]

        # Handle deprecated Num/Str nodes for older Python versions
        if hasattr(ast, 'Num'):
            allowed_nodes.append(ast.Num)
        if hasattr(ast, 'Str'):
            allowed_nodes.append(ast.Str)
        if hasattr(ast, 'NameConstant'):
            allowed_nodes.append(ast.NameConstant)

        allowed_nodes_tuple = tuple(allowed_nodes)

        for node in ast.walk(tree):
            # Check if node type is in allowed list
            if not isinstance(node, allowed_nodes_tuple):
                raise UnsafeExpressionError(
                    f"Unsafe AST node type: {type(node).__name__}"
                )

            # Additional validation for specific node types
            if isinstance(node, ast.Compare):
                # Check comparison operators
                for op in node.ops:
                    if type(op) not in SAFE_OPERATORS:
                        raise UnsafeExpressionError(
                            f"Unsafe comparison operator: {type(op).__name__}"
                        )
            elif isinstance(node, ast.BoolOp):
                # Check boolean operators (and, or)
                if type(node.op) not in SAFE_OPERATORS:
                    raise UnsafeExpressionError(
                        f"Unsafe boolean operator: {type(node.op).__name__}"
                    )
            elif isinstance(node, ast.UnaryOp):
                # Check unary operators (not)
                if type(node.op) not in SAFE_OPERATORS:
                    raise UnsafeExpressionError(
                        f"Unsafe unary operator: {type(node.op).__name__}"
                    )
            elif isinstance(node, ast.BinOp):
                # Allow basic arithmetic for numeric comparisons
                if type(node.op) not in SAFE_OPERATORS:
                    raise UnsafeExpressionError(
                        f"Unsafe binary operator: {type(node.op).__name__}"
                    )
            elif isinstance(node, ast.Call):
                # Allow only specific method calls on strings
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr not in [
                        "contains",
                        "startswith",
                        "endswith",
                        "lower",
                        "upper",
                        "strip",
                    ]:
                        raise UnsafeExpressionError(
                            f"Unsafe method call: {node.func.attr}"
                        )
                else:
                    raise UnsafeExpressionError("Function calls not allowed")

    def _eval_node(self, node: ast.AST) -> Any:
        """Recursively evaluate an AST node.

        Args:
            node: AST node to evaluate

        Returns:
            Result of evaluating the node

        Raises:
            ConditionEvaluationError: If node cannot be evaluated
        """
        if isinstance(node, ast.Constant):
            return node.value
        # Handle deprecated nodes for Python < 3.8
        elif hasattr(ast, 'Num') and isinstance(node, ast.Num):
            return node.n
        elif hasattr(ast, 'Str') and isinstance(node, ast.Str):
            return node.s
        elif hasattr(ast, 'NameConstant') and isinstance(node, ast.NameConstant):
            return node.value
        elif isinstance(node, ast.Name):
            # Resolve variable from context
            if node.id not in self.context:
                raise ConditionEvaluationError(
                    f"Variable '{node.id}' not found in context"
                )
            return self.context[node.id]
        elif isinstance(node, ast.Attribute):
            # Resolve attribute access (e.g., trigger.subject)
            value = self._eval_node(node.value)
            if isinstance(value, dict):
                if node.attr not in value:
                    raise ConditionEvaluationError(
                        f"Attribute '{node.attr}' not found"
                    )
                return value[node.attr]
            else:
                if not hasattr(value, node.attr):
                    raise ConditionEvaluationError(
                        f"Attribute '{node.attr}' not found"
                    )
                return getattr(value, node.attr)
        elif isinstance(node, ast.Compare):
            # Evaluate comparison (e.g., a > b)
            left = self._eval_node(node.left)
            result = True
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator)
                op_func = SAFE_OPERATORS.get(type(op))
                if op_func is None:
                    raise ConditionEvaluationError(
                        f"Operator {type(op).__name__} not supported"
                    )
                result = result and op_func(left, right)
                if not result:
                    break
                left = right
            return result
        elif isinstance(node, ast.BoolOp):
            # Evaluate boolean operation (and, or)
            op_func = SAFE_OPERATORS.get(type(node.op))
            if op_func is None:
                raise ConditionEvaluationError(
                    f"Boolean operator {type(node.op).__name__} not supported"
                )

            # For 'and' operator
            if isinstance(node.op, ast.And):
                result = True
                for value in node.values:
                    result = result and bool(self._eval_node(value))
                    if not result:
                        break
                return result
            # For 'or' operator
            elif isinstance(node.op, ast.Or):
                result = False
                for value in node.values:
                    result = result or bool(self._eval_node(value))
                    if result:
                        break
                return result
            else:
                raise ConditionEvaluationError(
                    f"Boolean operator {type(node.op).__name__} not supported"
                )
        elif isinstance(node, ast.UnaryOp):
            # Evaluate unary operation (not)
            if isinstance(node.op, ast.Not):
                return not bool(self._eval_node(node.operand))
            else:
                raise ConditionEvaluationError(
                    f"Unary operator {type(node.op).__name__} not supported"
                )
        elif isinstance(node, ast.BinOp):
            # Evaluate binary operation (arithmetic)
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_func = SAFE_OPERATORS.get(type(node.op))
            if op_func is None:
                raise ConditionEvaluationError(
                    f"Binary operator {type(node.op).__name__} not supported"
                )
            return op_func(left, right)
        elif isinstance(node, ast.Call):
            # Evaluate method calls
            if isinstance(node.func, ast.Attribute):
                obj = self._eval_node(node.func.value)
                method_name = node.func.attr

                # Evaluate arguments
                args = [self._eval_node(arg) for arg in node.args]

                # Call the method
                if hasattr(obj, method_name):
                    method = getattr(obj, method_name)
                    return method(*args)
                else:
                    raise ConditionEvaluationError(
                        f"Method '{method_name}' not found on object"
                    )
            else:
                raise ConditionEvaluationError("Invalid function call")
        else:
            raise ConditionEvaluationError(
                f"Unsupported AST node type: {type(node).__name__}"
            )


def evaluate_condition(
    condition_config: Dict[str, Any],
    context: Dict[str, Any],
) -> bool:
    """Evaluate a condition configuration against an execution context.

    Args:
        condition_config: Condition configuration from AreaStep.config
                         Expected format:
                         {
                             "conditionType": "simple" | "expression",
                             "simple": {
                                 "field": "trigger.subject",
                                 "operator": "contains",
                                 "value": "Invoice"
                             },
                             "expression": "trigger.amount > 100 and trigger.status == 'pending'"
                         }
        context: Execution context with variables (e.g., {"trigger": {...}, "now": {...}})

    Returns:
        Boolean result of the condition evaluation

    Raises:
        ConditionEvaluationError: If condition cannot be evaluated
    """
    evaluator = ConditionEvaluator(context)

    condition_type = condition_config.get("conditionType", "simple")

    if condition_type == "simple":
        simple_config = condition_config.get("simple")
        if not simple_config:
            raise ConditionEvaluationError(
                "Simple condition configuration missing"
            )

        field = simple_config.get("field")
        operator_name = simple_config.get("operator")
        value = simple_config.get("value")

        if not all([field, operator_name]):
            raise ConditionEvaluationError(
                "Simple condition must have 'field' and 'operator'"
            )

        return evaluator.evaluate_simple_condition(field, operator_name, value)

    elif condition_type == "expression":
        expression = condition_config.get("expression")
        if not expression:
            raise ConditionEvaluationError(
                "Expression condition missing 'expression' field"
            )

        return evaluator.evaluate_expression(expression)

    else:
        raise ConditionEvaluationError(
            f"Unknown condition type: {condition_type}"
        )


__all__ = [
    "ConditionEvaluator",
    "ConditionEvaluationError",
    "UnsafeExpressionError",
    "evaluate_condition",
]
