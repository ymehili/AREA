"""Tests for variable extraction functions."""

import pytest
from app.integrations.variable_extractor import (
    extract_gmail_variables,
    extract_google_drive_variables,
    extract_calendar_variables,
    extract_github_variables,
)


class TestVariableExtractor:
    """Test variable extraction functions."""

    def test_extract_gmail_variables_empty_input(self):
        """Test extracting Gmail variables with empty input."""
        result = extract_gmail_variables({})
        assert result == {}

        result = extract_gmail_variables(None)
        assert result == {}

    def test_extract_gmail_variables_with_payload(self):
        """Test extracting Gmail variables from payload."""
        trigger_data = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Test Email Subject"},
                    {"name": "Date", "value": "2023-01-01T10:00:00Z"},
                ]
            },
            "snippet": "This is the email snippet",
            "id": "msg123",
            "threadId": "thread456",
        }

        result = extract_gmail_variables(trigger_data)

        assert result["gmail.sender"] == "sender@example.com"
        assert result["gmail.subject"] == "Test Email Subject"
        assert result["gmail.timestamp"] == "2023-01-01T10:00:00Z"
        assert result["gmail.snippet"] == "This is the email snippet"
        assert result["gmail.message_id"] == "msg123"
        assert result["gmail.thread_id"] == "thread456"

    def test_extract_gmail_variables_with_body(self):
        """Test extracting Gmail variables including body content."""
        trigger_data = {
            "payload": {
                "headers": []
            },
            "body": "Full email body content",
            "attachments": ["file1.pdf", "file2.docx"]
        }

        result = extract_gmail_variables(trigger_data)

        assert result["gmail.body"] == "Full email body content"
        assert result["gmail.attachments"] == ["file1.pdf", "file2.docx"]

    def test_extract_google_drive_variables_empty_input(self):
        """Test extracting Google Drive variables with empty input."""
        result = extract_google_drive_variables({})
        assert result == {}

        result = extract_google_drive_variables(None)
        assert result == {}

    def test_extract_google_drive_variables(self):
        """Test extracting Google Drive variables."""
        trigger_data = {
            "fileId": "drive_file_123",
            "id": "drive_file_456",  # Alternative field name
            "name": "test_document.pdf",
            "mimeType": "application/pdf",
            "owners": [{"emailAddress": "owner@example.com"}],
            "webViewLink": "https://drive.google.com/file/d/drive_file_123/view",
            "createdTime": "2023-01-01T10:00:00Z",
            "modifiedTime": "2023-01-02T15:30:00Z",
            "size": "1024000",
            "description": "A test document"
        }

        result = extract_google_drive_variables(trigger_data)

        # The function uses fileId when present, which takes precedence over id
        assert result["drive.file_id"] == "drive_file_123"
        assert result["drive.file_name"] == "test_document.pdf"
        assert result["drive.mime_type"] == "application/pdf"
        assert result["drive.owner"] == "owner@example.com"
        assert result["drive.file_url"] == "https://drive.google.com/file/d/drive_file_123/view"
        assert result["drive.created_time"] == "2023-01-01T10:00:00Z"
        assert result["drive.modified_time"] == "2023-01-02T15:30:00Z"
        assert result["drive.file_size"] == "1024000"
        assert result["drive.description"] == "A test document"

    def test_extract_calendar_variables_empty_input(self):
        """Test extracting Calendar variables with empty input."""
        result = extract_calendar_variables({})
        assert result == {}

        result = extract_calendar_variables(None)
        assert result == {}

    def test_extract_calendar_variables(self):
        """Test extracting Calendar variables."""
        trigger_data = {
            "id": "cal_event_123",
            "summary": "Team Meeting",
            "description": "Weekly team sync meeting",
            "location": "Conference Room A",
            "start_time": "2023-01-01T10:00:00Z",
            "end_time": "2023-01-01T11:00:00Z",
            "timezone": "UTC",
            "attendees": ["user1@example.com", "user2@example.com"],
            "organizer": "organizer@example.com",
            "status": "confirmed",
            "html_link": "https://calendar.google.com/event123",
            "created": "2022-12-28T15:30:00Z",
            "updated": "2022-12-30T09:15:00Z",
            "is_all_day": False
        }

        result = extract_calendar_variables(trigger_data)

        assert result["calendar.event_id"] == "cal_event_123"
        assert result["calendar.title"] == "Team Meeting"
        assert result["calendar.summary"] == "Team Meeting"
        assert result["calendar.description"] == "Weekly team sync meeting"
        assert result["calendar.location"] == "Conference Room A"
        assert result["calendar.start_time"] == "2023-01-01T10:00:00Z"
        assert result["calendar.end_time"] == "2023-01-01T11:00:00Z"
        assert result["calendar.timezone"] == "UTC"
        assert result["calendar.attendees"] == "user1@example.com, user2@example.com"
        assert result["calendar.organizer"] == "organizer@example.com"
        assert result["calendar.status"] == "confirmed"
        assert result["calendar.link"] == "https://calendar.google.com/event123"
        assert result["calendar.html_link"] == "https://calendar.google.com/event123"
        assert result["calendar.created"] == "2022-12-28T15:30:00Z"
        assert result["calendar.updated"] == "2022-12-30T09:15:00Z"
        assert result["calendar.is_all_day"] == "False"

    def test_extract_calendar_variables_all_day(self):
        """Test extracting variables for an all-day event."""
        trigger_data = {
            "id": "cal_event_456",
            "summary": "Public Holiday",
            "start_time": "2023-01-01",  # Date instead of datetime
            "end_time": "2023-01-02",
            "is_all_day": True,
            "attendees": []  # Empty list
        }

        result = extract_calendar_variables(trigger_data)

        assert result["calendar.event_id"] == "cal_event_456"
        assert result["calendar.title"] == "Public Holiday"
        assert result["calendar.start_time"] == "2023-01-01"
        assert result["calendar.is_all_day"] == "True"
        assert result["calendar.attendees"] == ""  # Empty string for empty list

    def test_extract_github_variables_empty_input(self):
        """Test extracting GitHub variables with empty input."""
        result = extract_github_variables({})
        assert result == {}

        result = extract_github_variables(None)
        assert result == {}

    def test_extract_github_variables(self):
        """Test extracting GitHub variables."""
        trigger_data = {
            "repository": {
                "name": "test-repo",
                "full_name": "owner/test-repo",
                "html_url": "https://github.com/owner/test-repo"
            },
            "sender": {
                "login": "sender_user",
                "avatar_url": "https://avatars.githubusercontent.com/u/12345"
            },
            "issue": {
                "number": 1,
                "title": "Test Issue",
                "body": "Issue description",
                "user": {
                    "login": "issue_author"
                }
            },
            "pull_request": {
                "number": 2,
                "title": "Test PR",
                "body": "PR description",
                "user": {
                    "login": "pr_author"
                }
            },
            "action": "opened",
            "comment": {
                "body": "This is a comment",
                "user": {
                    "login": "comment_author"
                }
            },
            "commits": ["commit1", "commit2"],
            "ref": "refs/heads/main"
        }

        result = extract_github_variables(trigger_data)

        # Repository variables
        assert result["github.repo"] == "test-repo"
        assert result["github.repo_full_name"] == "owner/test-repo"
        assert result["github.repo_url"] == "https://github.com/owner/test-repo"

        # Sender variables
        assert result["github.sender"] == "sender_user"
        assert result["github.sender_avatar"] == "https://avatars.githubusercontent.com/u/12345"

        # Issue variables
        assert result["github.issue_number"] == 1
        assert result["github.issue_title"] == "Test Issue"
        assert result["github.issue_body"] == "Issue description"
        assert result["github.issue_author"] == "issue_author"

        # PR variables
        assert result["github.pull_request_number"] == 2
        assert result["github.pull_request_title"] == "Test PR"
        assert result["github.pull_request_body"] == "PR description"
        assert result["github.pull_request_author"] == "pr_author"

        # Action
        assert result["github.action"] == "opened"

        # Comment
        assert result["github.comment_body"] == "This is a comment"
        assert result["github.comment_author"] == "comment_author"

        # Commits and branch
        assert result["github.commits"] == ["commit1", "commit2"]
        assert result["github.branch"] == "main"

    def test_extract_github_variables_with_different_event_types(self):
        """Test extracting GitHub variables for different event types."""
        # Push event without issue or PR
        trigger_data = {
            "ref": "refs/heads/feature-branch",
            "commits": ["commit123"]
        }

        result = extract_github_variables(trigger_data)

        assert result["github.branch"] == "feature-branch"
        assert result["github.commits"] == ["commit123"]

        # Only repository information
        trigger_data = {
            "repository": {
                "name": "another-repo",
                "full_name": "org/another-repo"
            }
        }

        result = extract_github_variables(trigger_data)

        assert result["github.repo"] == "another-repo"
        assert result["github.repo_full_name"] == "org/another-repo"
        # Other variables should not be present
        assert "github.issue_number" not in result
        assert "github.pull_request_number" not in result