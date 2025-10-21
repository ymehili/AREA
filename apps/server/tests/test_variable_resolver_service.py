"""Tests for variable resolver service."""

import pytest
from app.services.variable_resolver import (
    extract_variables_from_trigger_data,
    substitute_variables_in_params,
    resolve_variables,
    get_available_variables_for_service,
    extract_variables_by_service,
)


class TestVariableResolver:
    """Test variable resolver functionality."""

    def test_extract_variables_from_trigger_data_simple(self):
        """Test extracting variables from simple trigger data."""
        trigger_data = {
            "message": "Hello World",
            "count": 42,
            "active": True
        }

        variables = extract_variables_from_trigger_data(trigger_data)

        assert variables["message"] == "Hello World"
        assert variables["count"] == 42
        assert variables["active"] is True

    def test_extract_variables_from_trigger_data_nested(self):
        """Test extracting variables from nested trigger data."""
        trigger_data = {
            "user": {
                "name": "John Doe",
                "email": "john@example.com",
                "profile": {
                    "age": 30,
                    "location": "New York"
                }
            },
            "timestamp": "2023-01-01T00:00:00Z"
        }

        variables = extract_variables_from_trigger_data(trigger_data)

        assert variables["user.name"] == "John Doe"
        assert variables["user.email"] == "john@example.com"
        assert variables["user.profile.age"] == 30
        assert variables["user.profile.location"] == "New York"
        assert variables["timestamp"] == "2023-01-01T00:00:00Z"

    def test_extract_variables_from_trigger_data_list(self):
        """Test extracting variables from trigger data with lists."""
        trigger_data = {
            "items": ["item1", "item2", "item3"],
            "metadata": {
                "tags": ["tag1", "tag2"]
            }
        }

        variables = extract_variables_from_trigger_data(trigger_data)

        assert variables["items.0"] == "item1"
        assert variables["items.1"] == "item2"
        assert variables["items.2"] == "item3"
        assert variables["metadata.tags.0"] == "tag1"
        assert variables["metadata.tags.1"] == "tag2"

    def test_substitute_variables_in_params_simple(self):
        """Test substituting variables in simple params."""
        params = {
            "message": "Hello {{user.name}}!",
            "count": "{{item.count}}",
            "description": "This is a test"
        }
        variables = {
            "user.name": "Alice",
            "item.count": 5
        }

        result = substitute_variables_in_params(params, variables)

        assert result["message"] == "Hello Alice!"
        assert result["count"] == 5  # Should be the actual value, not string
        assert result["description"] == "This is a test"

    def test_substitute_variables_in_params_nested(self):
        """Test substituting variables in nested params."""
        params = {
            "user": {
                "name": "{{user.name}}",
                "email": "{{user.email}}"
            },
            "settings": {
                "notifications": "{{settings.enabled}}"
            }
        }
        variables = {
            "user.name": "Bob",
            "user.email": "bob@example.com",
            "settings.enabled": True
        }

        result = substitute_variables_in_params(params, variables)

        assert result["user"]["name"] == "Bob"
        assert result["user"]["email"] == "bob@example.com"
        assert result["settings"]["notifications"] is True

    def test_substitute_variables_in_params_with_list(self):
        """Test substituting variables in params with lists."""
        params = {
            "recipients": ["{{user.email}}", "{{admin.email}}"],
            "tags": ["{{category}}", "important"]
        }
        variables = {
            "user.email": "user@example.com",
            "admin.email": "admin@example.com",
            "category": "urgent"
        }

        result = substitute_variables_in_params(params, variables)

        assert result["recipients"] == ["user@example.com", "admin@example.com"]
        assert result["tags"] == ["urgent", "important"]

    def test_substitute_variables_in_params_partial_replacement(self):
        """Test partial variable replacement in strings."""
        params = {
            "message": "Hello {{user.name}}, your order {{order.id}} is ready!",
            "subject": "Order {{order.id}} update"
        }
        variables = {
            "user.name": "Charlie",
            "order.id": "ORD-12345"
        }

        result = substitute_variables_in_params(params, variables)

        assert result["message"] == "Hello Charlie, your order ORD-12345 is ready!"
        assert result["subject"] == "Order ORD-12345 update"

    def test_resolve_variables_simple(self):
        """Test resolving variables in a simple template."""
        template = "Hello {{name}}!"
        variables = {"name": "World"}

        result = resolve_variables(template, variables)

        assert result == "Hello World!"

    def test_resolve_variables_with_missing_var(self):
        """Test resolving variables with a missing variable."""
        template = "Hello {{name}} and {{missing_var}}!"
        variables = {"name": "World"}

        result = resolve_variables(template, variables)

        # Missing variable should remain in the template
        assert result == "Hello World and {{missing_var}}!"

    def test_resolve_variables_with_nested_vars(self):
        """Test resolving variables with nested/dotted names."""
        template = "{{user.name}} from {{user.location}} says {{message}}"
        variables = {
            "user.name": "Alice",
            "user.location": "Paris",
            "message": "Bonjour!"
        }

        result = resolve_variables(template, variables)

        assert result == "Alice from Paris says Bonjour!"

    def test_resolve_variables_with_spaces(self):
        """Test resolving variables that have spaces around the name."""
        template = "Hello {{ name }}!"
        variables = {"name": "World"}

        result = resolve_variables(template, variables)

        assert result == "Hello World!"

    def test_get_available_variables_for_service(self):
        """Test getting available variables for a specific service."""
        # Test for a service with specific variables
        vars_for_gmail = get_available_variables_for_service("gmail", "receive_email")
        assert "gmail.sender" in vars_for_gmail
        assert "gmail.subject" in vars_for_gmail
        assert "now" in vars_for_gmail  # Common variable
        assert len(vars_for_gmail) > 5  # Should have several variables

        # Test for a service without specific variables
        vars_for_unknown = get_available_variables_for_service("unknown_service", "some_action")
        # Should only have common variables
        assert "now" in vars_for_unknown
        assert "timestamp" in vars_for_unknown
        assert "gmail.sender" not in vars_for_unknown  # Not specific to unknown service

        # Test for another service
        vars_for_github = get_available_variables_for_service("github", "issue_created")
        assert "github.repo" in vars_for_github
        assert "github.issue_number" in vars_for_github

    def test_extract_variables_by_service_with_namespaced_keys(self):
        """Test extracting variables when trigger_data already has namespaced keys."""
        trigger_data = {
            "gmail.sender": "sender@example.com",
            "gmail.subject": "Test Subject",
            "gmail.body": "Test Body",
            "now": "2023-01-01T00:00:00Z",
            "timestamp": 1234567890
        }

        variables = extract_variables_by_service(trigger_data, "gmail")

        # Should pass through the namespaced variables
        assert variables["gmail.sender"] == "sender@example.com"
        assert variables["gmail.subject"] == "Test Subject"
        assert variables["gmail.body"] == "Test Body"
        assert variables["now"] == "2023-01-01T00:00:00Z"
        assert variables["timestamp"] == 1234567890

    def test_extract_variables_by_service_with_service_type(self):
        """Test extracting variables using service-specific extractor."""
        trigger_data = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Test Email Subject"},
                ]
            },
            "snippet": "This is the email snippet"
        }

        variables = extract_variables_by_service(trigger_data, "gmail")

        # Should use the Gmail-specific extractor
        assert "gmail.sender" in variables
        assert "gmail.subject" in variables
        assert variables["gmail.sender"] == "sender@example.com"
        assert variables["gmail.subject"] == "Test Email Subject"