"""Tests for variable resolver functionality."""

import pytest
from app.services.variable_resolver import (
    extract_variables_from_trigger_data,
    substitute_variables_in_params,
    get_available_variables_for_service,
    extract_variables_by_service
)


def test_extract_variables_from_trigger_data_simple():
    """Test extracting variables from simple trigger data."""
    trigger_data = {
        "now": "2023-10-01T12:00:00Z",
        "user": {
            "id": "123",
            "name": "John Doe"
        }
    }
    
    variables = extract_variables_from_trigger_data(trigger_data)
    
    assert "now" in variables
    assert variables["now"] == "2023-10-01T12:00:00Z"
    assert "user.id" in variables
    assert variables["user.id"] == "123"
    assert "user.name" in variables
    assert variables["user.name"] == "John Doe"


def test_extract_variables_from_trigger_data_nested():
    """Test extracting variables from deeply nested trigger data."""
    trigger_data = {
        "email": {
            "sender": {
                "name": "Jane",
                "email": "jane@example.com"
            },
            "subject": "Test email",
            "attachments": [
                {"name": "file1.txt", "size": 1024},
                {"name": "file2.pdf", "size": 2048}
            ]
        }
    }
    
    variables = extract_variables_from_trigger_data(trigger_data)
    
    assert "email.sender.name" in variables
    assert variables["email.sender.name"] == "Jane"
    assert "email.sender.email" in variables
    assert variables["email.sender.email"] == "jane@example.com"
    assert "email.subject" in variables
    assert variables["email.subject"] == "Test email"
    # For list items, we expect indices
    assert "email.attachments.0.name" in variables
    assert variables["email.attachments.0.name"] == "file1.txt"


def test_substitute_variables_in_params():
    """Test substituting variables in parameters."""
    params = {
        "message": "Hello {{user.name}}, current time is {{now}}",
        "recipient": "{{user.email}}",
        "count": "{{user.count}}"
    }
    
    variables = {
        "user.name": "John Doe",
        "user.email": "john@example.com",
        "user.count": 5,
        "now": "2023-10-01T12:00:00Z"
    }
    
    result = substitute_variables_in_params(params, variables)
    
    assert result["message"] == "Hello John Doe, current time is 2023-10-01T12:00:00Z"
    assert result["recipient"] == "john@example.com"
    assert result["count"] == 5  # Should be the actual value, not string


def test_substitute_variables_in_params_full_substitution():
    """Test when entire parameter is a variable."""
    params = {
        "user_id": "{{user.id}}",
        "message": "Hello {{user.name}}"
    }
    
    variables = {
        "user.id": 123,
        "user.name": "John"
    }
    
    result = substitute_variables_in_params(params, variables)
    
    assert result["user_id"] == 123  # Should be the actual value, not string
    assert result["message"] == "Hello John"


def test_substitute_variables_in_params_nested():
    """Test substituting variables in nested structures."""
    params = {
        "config": {
            "name": "{{user.name}}",
            "details": [
                {"value": "{{user.id}}"},
                {"note": "Time: {{now}}"}
            ]
        }
    }
    
    variables = {
        "user.name": "John",
        "user.id": 123,
        "now": "2023-10-01"
    }
    
    result = substitute_variables_in_params(params, variables)
    
    assert result["config"]["name"] == "John"
    assert result["config"]["details"][0]["value"] == 123
    assert result["config"]["details"][1]["note"] == "Time: 2023-10-01"


def test_get_available_variables_for_service():
    """Test getting available variables for different services."""
    # Test common variables
    variables = get_available_variables_for_service("any_service", "")
    assert "now" in variables
    assert "user.id" in variables
    assert "area.id" in variables
    
    # Test Gmail-specific variables
    gmail_vars = get_available_variables_for_service("gmail", "")
    assert "gmail.sender" in gmail_vars
    assert "gmail.subject" in gmail_vars
    
    # Test Google Drive-specific variables
    drive_vars = get_available_variables_for_service("google_drive", "")
    assert "drive.file_id" in drive_vars
    assert "drive.file_name" in drive_vars
    
    # Test GitHub-specific variables
    github_vars = get_available_variables_for_service("github", "")
    assert "github.repo" in github_vars
    assert "github.issue_number" in github_vars


def test_extract_variables_by_service_gmail():
    """Test extracting variables using Gmail-specific extractor."""
    trigger_data = {
        "id": "12345",
        "threadId": "thread123",
        "snippet": "This is a test email",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "Subject", "value": "Test Subject"},
                {"name": "Date", "value": "2023-10-01T12:00:00Z"}
            ]
        }
    }
    
    variables = extract_variables_by_service(trigger_data, "gmail")
    
    # Check that Gmail-specific variables are present
    assert "gmail.sender" in variables
    assert variables["gmail.sender"] == "sender@example.com"
    assert "gmail.subject" in variables
    assert variables["gmail.subject"] == "Test Subject"
    assert "gmail.message_id" in variables
    assert variables["gmail.message_id"] == "12345"


def test_extract_variables_by_service_google_drive():
    """Test extracting variables using Google Drive-specific extractor."""
    trigger_data = {
        "fileId": "drive123",
        "name": "test_document.docx",
        "mimeType": "application/vnd.google-apps.document",
        "owners": [{"emailAddress": "owner@example.com"}],
        "webViewLink": "https://drive.google.com/file/d/drive123",
        "createdTime": "2023-10-01T12:00:00Z",
        "modifiedTime": "2023-10-01T13:00:00Z",
        "size": "123456"
    }
    
    variables = extract_variables_by_service(trigger_data, "google_drive")
    
    # Check that Google Drive-specific variables are present
    assert "drive.file_id" in variables
    assert variables["drive.file_id"] == "drive123"
    assert "drive.file_name" in variables
    assert variables["drive.file_name"] == "test_document.docx"
    assert "drive.owner" in variables
    assert variables["drive.owner"] == "owner@example.com"


def test_extract_variables_by_service_github():
    """Test extracting variables using GitHub-specific extractor."""
    trigger_data = {
        "action": "opened",
        "repository": {
            "name": "test-repo",
            "full_name": "user/test-repo",
            "html_url": "https://github.com/user/test-repo"
        },
        "sender": {
            "login": "testuser",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345"
        },
        "issue": {
            "number": 1,
            "title": "Test Issue",
            "body": "This is a test issue",
            "user": {"login": "issue_author"}
        }
    }
    
    variables = extract_variables_by_service(trigger_data, "github")
    
    # Check that GitHub-specific variables are present
    assert "github.repo" in variables
    assert variables["github.repo"] == "test-repo"
    assert "github.sender" in variables
    assert variables["github.sender"] == "testuser"
    assert "github.issue_number" in variables
    assert variables["github.issue_number"] == 1


def test_extract_variables_by_service_unknown_service():
    """Test that unknown service falls back to generic extractor."""
    trigger_data = {
        "simple": "value",
        "nested": {
            "key": "data"
        }
    }
    
    variables = extract_variables_by_service(trigger_data, "unknown_service")
    
    # Should fall back to generic extraction
    assert "simple" in variables
    assert variables["simple"] == "value"
    assert "nested.key" in variables
    assert variables["nested.key"] == "data"