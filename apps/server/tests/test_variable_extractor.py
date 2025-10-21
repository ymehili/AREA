"""Tests for variable extractor module."""

from __future__ import annotations

from app.integrations.variable_extractor import (
    extract_gmail_variables,
    extract_google_drive_variables,
    extract_calendar_variables,
    extract_github_variables,
)


class TestGmailVariableExtractor:
    """Test Gmail variable extraction."""

    def test_extract_gmail_variables_complete(self):
        """Test extracting all Gmail variables from complete event data."""
        trigger_data = {
            'id': 'msg123',
            'threadId': 'thread456',
            'snippet': 'This is a preview...',
            'body': 'Full email body content',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'Subject', 'value': 'Test Email'},
                    {'name': 'Date', 'value': '2023-10-01 12:00:00'},
                ]
            },
            'attachments': ['file1.pdf', 'file2.doc']
        }
        
        variables = extract_gmail_variables(trigger_data)
        
        assert variables['gmail.sender'] == 'sender@example.com'
        assert variables['gmail.subject'] == 'Test Email'
        assert variables['gmail.timestamp'] == '2023-10-01 12:00:00'
        assert variables['gmail.snippet'] == 'This is a preview...'
        assert variables['gmail.body'] == 'Full email body content'
        assert variables['gmail.message_id'] == 'msg123'
        assert variables['gmail.thread_id'] == 'thread456'
        assert variables['gmail.attachments'] == ['file1.pdf', 'file2.doc']

    def test_extract_gmail_variables_empty_data(self):
        """Test extracting Gmail variables from empty data."""
        variables = extract_gmail_variables({})
        assert variables == {}
        
        variables = extract_gmail_variables(None)
        assert variables == {}

    def test_extract_gmail_variables_partial_data(self):
        """Test extracting Gmail variables from partial data."""
        trigger_data = {
            'id': 'msg123',
            'snippet': 'Preview only'
        }
        
        variables = extract_gmail_variables(trigger_data)
        
        assert variables['gmail.message_id'] == 'msg123'
        assert variables['gmail.snippet'] == 'Preview only'
        assert 'gmail.sender' not in variables
        assert 'gmail.subject' not in variables

    def test_extract_gmail_variables_headers_only(self):
        """Test extracting Gmail variables with headers only."""
        trigger_data = {
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Important Message'},
                ]
            }
        }
        
        variables = extract_gmail_variables(trigger_data)
        
        assert variables['gmail.subject'] == 'Important Message'
        assert 'gmail.sender' not in variables

    def test_extract_gmail_variables_missing_header_values(self):
        """Test extracting Gmail variables with missing header values."""
        trigger_data = {
            'payload': {
                'headers': [
                    {'name': 'From'},  # Missing value
                    {'value': 'test@example.com'},  # Missing name
                ]
            }
        }
        
        variables = extract_gmail_variables(trigger_data)
        
        # Should handle gracefully
        assert isinstance(variables, dict)

    def test_extract_gmail_variables_no_extracted_vars(self):
        """Test extracting Gmail variables when nothing matches."""
        trigger_data = {
            'random_field': 'random_value',
        }
        
        variables = extract_gmail_variables(trigger_data)
        
        # Should return empty dict when no variables extracted
        assert variables == {}


class TestGoogleDriveVariableExtractor:
    """Test Google Drive variable extraction."""

    def test_extract_drive_variables_complete(self):
        """Test extracting all Drive variables from complete event data."""
        trigger_data = {
            'id': 'file123',
            'name': 'document.pdf',
            'mimeType': 'application/pdf',
            'owners': [{'emailAddress': 'owner@example.com'}],
            'webViewLink': 'https://drive.google.com/file/d/file123/view',
            'createdTime': '2023-10-01T10:00:00Z',
            'modifiedTime': '2023-10-01T12:00:00Z',
            'size': '1024',
            'description': 'Important document'
        }
        
        variables = extract_google_drive_variables(trigger_data)
        
        assert variables['drive.file_id'] == 'file123'
        assert variables['drive.file_name'] == 'document.pdf'
        assert variables['drive.mime_type'] == 'application/pdf'
        assert variables['drive.owner'] == 'owner@example.com'
        assert variables['drive.file_url'] == 'https://drive.google.com/file/d/file123/view'
        assert variables['drive.created_time'] == '2023-10-01T10:00:00Z'
        assert variables['drive.modified_time'] == '2023-10-01T12:00:00Z'
        assert variables['drive.file_size'] == '1024'
        assert variables['drive.description'] == 'Important document'

    def test_extract_drive_variables_fileId_field(self):
        """Test extracting Drive variables using fileId field."""
        trigger_data = {
            'fileId': 'file456',
            'name': 'spreadsheet.xlsx'
        }
        
        variables = extract_google_drive_variables(trigger_data)
        
        assert variables['drive.file_id'] == 'file456'
        assert variables['drive.file_name'] == 'spreadsheet.xlsx'

    def test_extract_drive_variables_empty_owners(self):
        """Test extracting Drive variables with empty owners list."""
        trigger_data = {
            'id': 'file789',
            'owners': []
        }
        
        variables = extract_google_drive_variables(trigger_data)
        
        assert variables['drive.file_id'] == 'file789'
        assert 'drive.owner' not in variables

    def test_extract_drive_variables_empty_data(self):
        """Test extracting Drive variables from empty data."""
        variables = extract_google_drive_variables({})
        assert variables == {}
        
        variables = extract_google_drive_variables(None)
        assert variables == {}

    def test_extract_drive_variables_partial_data(self):
        """Test extracting Drive variables from partial data."""
        trigger_data = {
            'name': 'test.txt',
            'size': '512'
        }
        
        variables = extract_google_drive_variables(trigger_data)
        
        assert variables['drive.file_name'] == 'test.txt'
        assert variables['drive.file_size'] == '512'
        assert 'drive.file_id' not in variables

    def test_extract_drive_variables_no_extracted_vars(self):
        """Test extracting Drive variables when nothing matches."""
        trigger_data = {
            'random_field': 'random_value',
        }
        
        variables = extract_google_drive_variables(trigger_data)
        
        # Should return empty dict when no variables extracted
        assert variables == {}


class TestCalendarVariableExtractor:
    """Test Google Calendar variable extraction."""

    def test_extract_calendar_variables_complete(self):
        """Test extracting all Calendar variables from complete event data."""
        trigger_data = {
            'id': 'event123',
            'summary': 'Team Meeting',
            'description': 'Weekly sync meeting',
            'location': 'Conference Room A',
            'start_time': '2023-10-01T14:00:00Z',
            'end_time': '2023-10-01T15:00:00Z',
            'timezone': 'America/New_York',
            'attendees': ['alice@example.com', 'bob@example.com'],
            'organizer': 'manager@example.com',
            'status': 'confirmed',
            'html_link': 'https://calendar.google.com/event?eid=event123',
            'created': '2023-09-01T10:00:00Z',
            'updated': '2023-09-15T12:00:00Z',
            'is_all_day': False
        }
        
        variables = extract_calendar_variables(trigger_data)
        
        assert variables['calendar.event_id'] == 'event123'
        assert variables['calendar.title'] == 'Team Meeting'
        assert variables['calendar.summary'] == 'Team Meeting'
        assert variables['calendar.description'] == 'Weekly sync meeting'
        assert variables['calendar.location'] == 'Conference Room A'
        assert variables['calendar.start_time'] == '2023-10-01T14:00:00Z'
        assert variables['calendar.end_time'] == '2023-10-01T15:00:00Z'
        assert variables['calendar.timezone'] == 'America/New_York'
        assert variables['calendar.attendees'] == 'alice@example.com, bob@example.com'
        assert variables['calendar.organizer'] == 'manager@example.com'
        assert variables['calendar.status'] == 'confirmed'
        assert variables['calendar.link'] == 'https://calendar.google.com/event?eid=event123'
        assert variables['calendar.html_link'] == 'https://calendar.google.com/event?eid=event123'
        assert variables['calendar.created'] == '2023-09-01T10:00:00Z'
        assert variables['calendar.updated'] == '2023-09-15T12:00:00Z'
        assert variables['calendar.is_all_day'] == 'False'

    def test_extract_calendar_variables_attendees_string(self):
        """Test extracting Calendar variables with attendees as string."""
        trigger_data = {
            'id': 'event456',
            'summary': 'One-on-One',
            'attendees': 'john@example.com'  # String instead of list
        }
        
        variables = extract_calendar_variables(trigger_data)
        
        assert variables['calendar.event_id'] == 'event456'
        assert variables['calendar.attendees'] == 'john@example.com'

    def test_extract_calendar_variables_empty_data(self):
        """Test extracting Calendar variables from empty data."""
        variables = extract_calendar_variables({})
        assert variables == {}
        
        variables = extract_calendar_variables(None)
        assert variables == {}

    def test_extract_calendar_variables_partial_data(self):
        """Test extracting Calendar variables from partial data."""
        trigger_data = {
            'summary': 'Quick Meeting',
            'start_time': '2023-10-01T16:00:00Z'
        }
        
        variables = extract_calendar_variables(trigger_data)
        
        assert variables['calendar.title'] == 'Quick Meeting'
        assert variables['calendar.summary'] == 'Quick Meeting'
        assert variables['calendar.start_time'] == '2023-10-01T16:00:00Z'
        assert 'calendar.event_id' not in variables

    def test_extract_calendar_variables_no_extracted_vars(self):
        """Test extracting Calendar variables when nothing matches."""
        trigger_data = {
            'random_field': 'random_value',
        }
        
        variables = extract_calendar_variables(trigger_data)
        
        # Should return empty dict when no variables extracted
        assert variables == {}


class TestGitHubVariableExtractor:
    """Test GitHub variable extraction."""

    def test_extract_github_variables_issue_event(self):
        """Test extracting GitHub variables from issue event."""
        trigger_data = {
            'action': 'opened',
            'repository': {
                'name': 'test-repo',
                'full_name': 'user/test-repo',
                'html_url': 'https://github.com/user/test-repo'
            },
            'sender': {
                'login': 'developer',
                'avatar_url': 'https://github.com/avatars/developer.png'
            },
            'issue': {
                'number': 42,
                'title': 'Bug Report',
                'body': 'Description of the bug',
                'user': {
                    'login': 'reporter'
                }
            }
        }
        
        variables = extract_github_variables(trigger_data)
        
        assert variables['github.repo'] == 'test-repo'
        assert variables['github.repo_full_name'] == 'user/test-repo'
        assert variables['github.repo_url'] == 'https://github.com/user/test-repo'
        assert variables['github.sender'] == 'developer'
        assert variables['github.sender_avatar'] == 'https://github.com/avatars/developer.png'
        assert variables['github.action'] == 'opened'
        assert variables['github.issue_number'] == 42
        assert variables['github.issue_title'] == 'Bug Report'
        assert variables['github.issue_body'] == 'Description of the bug'
        assert variables['github.issue_author'] == 'reporter'

    def test_extract_github_variables_pull_request_event(self):
        """Test extracting GitHub variables from pull request event."""
        trigger_data = {
            'action': 'opened',
            'repository': {
                'name': 'test-repo',
                'full_name': 'user/test-repo',
                'html_url': 'https://github.com/user/test-repo'
            },
            'pull_request': {
                'number': 123,
                'title': 'New Feature',
                'body': 'Implementation details',
                'user': {
                    'login': 'contributor'
                }
            }
        }
        
        variables = extract_github_variables(trigger_data)
        
        assert variables['github.pull_request_number'] == 123
        assert variables['github.pull_request_title'] == 'New Feature'
        assert variables['github.pull_request_body'] == 'Implementation details'
        assert variables['github.pull_request_author'] == 'contributor'

    def test_extract_github_variables_comment_event(self):
        """Test extracting GitHub variables from comment event."""
        trigger_data = {
            'comment': {
                'body': 'Great work!',
                'user': {
                    'login': 'reviewer'
                }
            }
        }
        
        variables = extract_github_variables(trigger_data)
        
        assert variables['github.comment_body'] == 'Great work!'
        assert variables['github.comment_author'] == 'reviewer'

    def test_extract_github_variables_push_event(self):
        """Test extracting GitHub variables from push event."""
        trigger_data = {
            'ref': 'refs/heads/main',
            'commits': [
                {'id': 'abc123', 'message': 'First commit'},
                {'id': 'def456', 'message': 'Second commit'}
            ]
        }
        
        variables = extract_github_variables(trigger_data)
        
        assert variables['github.branch'] == 'main'
        assert len(variables['github.commits']) == 2

    def test_extract_github_variables_empty_data(self):
        """Test extracting GitHub variables from empty data."""
        variables = extract_github_variables({})
        assert variables == {}
        
        variables = extract_github_variables(None)
        assert variables == {}

    def test_extract_github_variables_partial_data(self):
        """Test extracting GitHub variables from partial data."""
        trigger_data = {
            'action': 'closed',
            'repository': {
                'name': 'my-repo'
            }
        }
        
        variables = extract_github_variables(trigger_data)
        
        assert variables['github.action'] == 'closed'
        assert variables['github.repo'] == 'my-repo'
        assert 'github.issue_number' not in variables

    def test_extract_github_variables_missing_nested_values(self):
        """Test extracting GitHub variables with missing nested values."""
        trigger_data = {
            'issue': {
                'number': 99
                # Missing title, body, user
            },
            'repository': {
                # Missing name, full_name, html_url
            }
        }
        
        variables = extract_github_variables(trigger_data)
        
        assert variables['github.issue_number'] == 99
        # Should handle missing values gracefully
        assert isinstance(variables, dict)

    def test_extract_github_variables_no_extracted_vars(self):
        """Test extracting GitHub variables when nothing matches."""
        trigger_data = {
            'random_field': 'random_value',
        }
        
        variables = extract_github_variables(trigger_data)
        
        # Should return empty dict when no variables extracted
        assert variables == {}

