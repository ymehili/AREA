"""Immutable catalog definitions for service actions and reactions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final, Optional, Dict, Any


@dataclass(frozen=True)
class AutomationOption:
    """A single automation option exposed by a third-party service."""

    key: str
    name: str
    description: str
    params: Optional[Dict[str, Any]] = None
    outputs: tuple[str, ...] = ()  # Variables produced by this trigger/action


@dataclass(frozen=True)
class ServiceIntegration:
    """Integration metadata bundling actions and reactions for a service."""

    slug: str
    name: str
    description: str
    actions: tuple[AutomationOption, ...]
    reactions: tuple[AutomationOption, ...]


SERVICE_CATALOG: Final[tuple[ServiceIntegration, ...]] = (
    ServiceIntegration(
        slug="time",
        name="Time",
        description="Time-based triggers for scheduled automation workflows.",
        actions=(
            AutomationOption(
                key="every_interval",
                name="Every Interval",
                description="Triggers at regular intervals (configurable in seconds).",
                params={
                    "interval": {
                        "type": "number",
                        "label": "Interval (seconds)",
                        "placeholder": "e.g. 60"
                    }
                },
            ),
        ),
        reactions=(),
    ),
    ServiceIntegration(
        slug="debug",
        name="Debug",
        description="Debugging and logging utilities for development and testing.",
        actions=(),
        reactions=(
            AutomationOption(
                key="log",
                name="Log Message",
                description="Logs a message to the application logs.",
                params={
                    "message": {
                        "type": "text",
                        "label": "Log Message",
                        "placeholder": "e.g., Email from {{gmail.sender}}: {{gmail.subject}}"
                    }
                },
            ),
        ),
    ),
    ServiceIntegration(
        slug="delay",
        name="Delay",
        description="Add a pause between steps in your automation workflow.",
        actions=(),
        reactions=(
            AutomationOption(
                key="wait",
                name="Wait for Duration",
                description="Pause the execution for a specified duration (seconds, minutes, hours, days).",
                params={
                    "duration": {
                        "type": "number",
                        "label": "Duration",
                        "placeholder": "e.g. 30"
                    },
                    "unit": {
                        "type": "select",
                        "label": "Unit",
                        "options": ["seconds", "minutes", "hours", "days"]
                    }
                },
            ),
        ),
    ),
    ServiceIntegration(
        slug="gmail",
        name="Gmail",
        description="Automate workflows around incoming and outgoing email events.",
        actions=(
            AutomationOption(
                key="new_email",
                name="New Email Received",
                description="Triggers when a new email arrives in the inbox.",
                params=None,
            ),
            AutomationOption(
                key="new_email_from_sender",
                name="New Email from Sender",
                description="Triggers when a new email arrives from a specific sender.",
                params={
                    "sender": {
                        "type": "text",
                        "label": "Sender Email",
                        "placeholder": "example@gmail.com"
                    }
                },
            ),
            AutomationOption(
                key="new_unread_email",
                name="New Unread Email",
                description="Triggers when a new unread email arrives in the inbox.",
                params=None,
            ),
            AutomationOption(
                key="email_starred",
                name="Email Starred",
                description="Triggers when a message is starred by the user.",
                params={
                    "message_id": {
                        "type": "text",
                        "label": "Message ID",
                        "placeholder": "{{gmail.message_id}}"
                    }
                },
            ),
        ),
        reactions=(
            AutomationOption(
                key="send_email",
                name="Send Email",
                description="Send an email message to one or more recipients.",
                params={
                    "to": {
                        "type": "text",
                        "label": "Recipient(s)",
                        "placeholder": "user@example.com"
                    },
                    "subject": {
                        "type": "text",
                        "label": "Subject",
                        "placeholder": "Email subject"
                    },
                    "body": {
                        "type": "text",
                        "label": "Body",
                        "placeholder": "Email body"
                    }
                },
            ),
            AutomationOption(
                key="mark_as_read",
                name="Mark as Read",
                description="Mark a specific email message as read.",
                params={
                    "message_id": {
                        "type": "text",
                        "label": "Message ID",
                        "placeholder": "{{gmail.message_id}}"
                    }
                },
            ),
            AutomationOption(
                key="forward_email",
                name="Forward Email",
                description="Forward an email message to another recipient.",
                params={
                    "message_id": {
                        "type": "text",
                        "label": "Message ID",
                        "placeholder": "{{gmail.message_id}}"
                    },
                    "to": {
                        "type": "text",
                        "label": "Forward To",
                        "placeholder": "recipient@example.com"
                    },
                    "comment": {
                        "type": "text",
                        "label": "Comment (optional)",
                        "placeholder": "Add a note before the forwarded content"
                    }
                },
            ),
        ),
    ),
    ServiceIntegration(
        slug="outlook",
        name="Outlook",
        description="Automate workflows around Outlook/Microsoft 365 email events.",
        actions=(
            AutomationOption(
                key="new_email",
                name="New Email Received",
                description="Triggers when a new email arrives in the Outlook inbox.",
            ),
            AutomationOption(
                key="new_email_from_sender",
                name="New Email from Sender",
                description="Triggers when a new email arrives from a specific sender.",
            ),
            AutomationOption(
                key="new_unread_email",
                name="New Unread Email",
                description="Triggers when a new unread email arrives in the inbox.",
            ),
            AutomationOption(
                key="email_flagged",
                name="Email Flagged",
                description="Triggers when an email is flagged/marked for follow-up.",
            ),
        ),
        reactions=(
            AutomationOption(
                key="send_email",
                name="Send Email",
                description="Send an email message to one or more recipients via Outlook.",
            ),
            AutomationOption(
                key="mark_as_read",
                name="Mark as Read",
                description="Mark a specific email message as read in Outlook.",
            ),
            AutomationOption(
                key="forward_email",
                name="Forward Email",
                description="Forward an email message to another recipient via Outlook.",
            ),
        ),
    ),
    ServiceIntegration(
        slug="google_drive",
        name="Google Drive",
        description="Manage files and folders stored in Google Drive.",
        actions=(
            AutomationOption(
                key="new_file",
                name="New File Created",
                description="Triggers when any new file is created in your Drive.",
            ),
            AutomationOption(
                key="file_modified",
                name="File Modified",
                description="Triggers when an existing file is modified in your Drive.",
            ),
            AutomationOption(
                key="file_in_folder",
                name="New File in Folder",
                description="Triggers when a new file is added to a specific folder.",
                params={
                    "folder_id": {
                        "type": "text",
                        "label": "Folder ID",
                        "placeholder": "Google Drive folder ID"
                    }
                },
            ),
            AutomationOption(
                key="file_shared_with_me",
                name="File Shared With Me",
                description="Triggers when someone shares a file with you.",
            ),
            AutomationOption(
                key="file_trashed",
                name="File Trashed",
                description="Triggers when a file is moved to trash.",
            ),
        ),
        reactions=(
            AutomationOption(
                key="upload_file",
                name="Upload File",
                description="Upload a new file to Drive.",
                params={
                    "file_name": {
                        "type": "text",
                        "label": "File Name",
                        "placeholder": "e.g., document.pdf"
                    },
                    "file_content": {
                        "type": "text",
                        "label": "File Content",
                        "placeholder": "Content of the file"
                    },
                    "folder_id": {
                        "type": "text",
                        "label": "Folder ID (optional)",
                        "placeholder": "Leave empty for root folder"
                    },
                    "mime_type": {
                        "type": "text",
                        "label": "MIME Type (optional)",
                        "placeholder": "e.g., application/pdf"
                    }
                },
            ),
            AutomationOption(
                key="create_folder",
                name="Create Folder",
                description="Create a new folder in Drive.",
                params={
                    "folder_name": {
                        "type": "text",
                        "label": "Folder Name",
                        "placeholder": "e.g., New Folder"
                    },
                    "parent_folder_id": {
                        "type": "text",
                        "label": "Parent Folder ID (optional)",
                        "placeholder": "Leave empty for root folder"
                    }
                },
            ),
            AutomationOption(
                key="copy_file",
                name="Copy File",
                description="Create a copy of an existing file.",
                params={
                    "file_id": {
                        "type": "text",
                        "label": "File ID",
                        "placeholder": "Google Drive file ID"
                    },
                    "new_name": {
                        "type": "text",
                        "label": "New Name (optional)",
                        "placeholder": "Leave empty to use original name"
                    }
                },
            ),
            AutomationOption(
                key="move_file",
                name="Move File",
                description="Move a file to another folder.",
                params={
                    "file_id": {
                        "type": "text",
                        "label": "File ID",
                        "placeholder": "Google Drive file ID"
                    },
                    "destination_folder_id": {
                        "type": "text",
                        "label": "Destination Folder ID",
                        "placeholder": "Google Drive folder ID"
                    }
                },
            ),
            AutomationOption(
                key="delete_file",
                name="Delete File",
                description="Move a file to trash.",
                params={
                    "file_id": {
                        "type": "text",
                        "label": "File ID",
                        "placeholder": "Google Drive file ID"
                    }
                },
            ),
        ),
    ),
    ServiceIntegration(
        slug="github",
        name="GitHub",
        description="Automate workflows around repository events and issue management.",
        actions=(
            AutomationOption(
                key="push_to_repository",
                name="Push to Repository",
                description="Triggers when code is pushed to a repository.",
                params=None,
            ),
            AutomationOption(
                key="new_issue",
                name="New Issue Created",
                description="Triggers when a new issue is created in a repository.",
                params=None,
            ),
            AutomationOption(
                key="pull_request_opened",
                name="Pull Request Opened",
                description="Triggers when a new pull request is opened.",
                params=None,
            ),
            AutomationOption(
                key="release_published",
                name="Release Published",
                description="Triggers when a new release is published.",
                params=None,
            ),
        ),
        reactions=(
            AutomationOption(
                key="create_issue",
                name="Create Issue",
                description="Create a new issue in a repository.",
                params={
                    "repo_owner": {
                        "type": "text",
                        "label": "Repository Owner",
                        "placeholder": "e.g., octocat"
                    },
                    "repo_name": {
                        "type": "text",
                        "label": "Repository Name",
                        "placeholder": "e.g., Hello-World"
                    },
                    "title": {
                        "type": "text",
                        "label": "Issue Title",
                        "placeholder": "e.g., Bug in authentication"
                    },
                    "body": {
                        "type": "text",
                        "label": "Issue Body",
                        "placeholder": "Describe the issue..."
                    },
                    "labels": {
                        "type": "text",
                        "label": "Labels (optional, comma-separated)",
                        "placeholder": "bug, help wanted"
                    }
                },
            ),
            AutomationOption(
                key="add_comment",
                name="Add Comment",
                description="Add a comment to an issue or pull request.",
                params={
                    "repo_owner": {
                        "type": "text",
                        "label": "Repository Owner",
                        "placeholder": "e.g., octocat"
                    },
                    "repo_name": {
                        "type": "text",
                        "label": "Repository Name",
                        "placeholder": "e.g., Hello-World"
                    },
                    "issue_number": {
                        "type": "text",
                        "label": "Issue/PR Number",
                        "placeholder": "e.g., 42 or {{github.issue_number}}"
                    },
                    "body": {
                        "type": "text",
                        "label": "Comment",
                        "placeholder": "Your comment..."
                    }
                },
            ),
            AutomationOption(
                key="close_issue",
                name="Close Issue",
                description="Close an issue in a repository.",
                params={
                    "repo_owner": {
                        "type": "text",
                        "label": "Repository Owner",
                        "placeholder": "e.g., octocat"
                    },
                    "repo_name": {
                        "type": "text",
                        "label": "Repository Name",
                        "placeholder": "e.g., Hello-World"
                    },
                    "issue_number": {
                        "type": "text",
                        "label": "Issue Number",
                        "placeholder": "e.g., 42 or {{github.issue_number}}"
                    }
                },
            ),
            AutomationOption(
                key="add_label",
                name="Add Label",
                description="Add labels to an issue or pull request.",
                params={
                    "repo_owner": {
                        "type": "text",
                        "label": "Repository Owner",
                        "placeholder": "e.g., octocat"
                    },
                    "repo_name": {
                        "type": "text",
                        "label": "Repository Name",
                        "placeholder": "e.g., Hello-World"
                    },
                    "issue_number": {
                        "type": "text",
                        "label": "Issue/PR Number",
                        "placeholder": "e.g., 42 or {{github.issue_number}}"
                    },
                    "labels": {
                        "type": "text",
                        "label": "Labels (comma-separated)",
                        "placeholder": "bug, enhancement"
                    }
                },
            ),
            AutomationOption(
                key="create_branch",
                name="Create Branch",
                description="Create a new branch in a repository.",
                params={
                    "repo_owner": {
                        "type": "text",
                        "label": "Repository Owner",
                        "placeholder": "e.g., octocat"
                    },
                    "repo_name": {
                        "type": "text",
                        "label": "Repository Name",
                        "placeholder": "e.g., Hello-World"
                    },
                    "branch_name": {
                        "type": "text",
                        "label": "New Branch Name",
                        "placeholder": "e.g., feature-123"
                    },
                    "from_branch": {
                        "type": "text",
                        "label": "From Branch (optional)",
                        "placeholder": "main (default)"
                    }
                },
            ),
        ),
    ),
    ServiceIntegration(
        slug="weather",
        name="Weather",
        description="Get current weather data and forecasts for any location worldwide.",
        actions=(
            AutomationOption(
                key="temperature_threshold",
                name="Temperature Threshold",
                description="Triggers when temperature reaches a specified threshold (above/below).",
                params={
                    "location": {
                        "type": "text",
                        "label": "Location",
                        "placeholder": "London,UK or Paris,FR"
                    },
                    "threshold": {
                        "type": "number",
                        "label": "Temperature Threshold",
                        "placeholder": "e.g. 20"
                    },
                    "condition": {
                        "type": "select",
                        "label": "Condition",
                        "options": ["above", "below"]
                    }
                },
            ),
            AutomationOption(
                key="weather_condition",
                name="Weather Condition",
                description="Triggers when specific weather condition occurs (rain, snow, clear, etc.).",
                params={
                    "location": {
                        "type": "text",
                        "label": "Location",
                        "placeholder": "London,UK or Paris,FR"
                    },
                    "condition": {
                        "type": "select",
                        "label": "Condition",
                        "options": ["clear", "clouds", "rain", "drizzle", "thunderstorm", "snow", "mist", "fog"]
                    }
                },
            ),
        ),
        reactions=(
            AutomationOption(
                key="get_current_weather",
                name="Get Current Weather",
                description="Fetch current weather data for a specified location (city name or coordinates).",
                params={
                    "location": {
                        "type": "text",
                        "label": "Location (City)",
                        "placeholder": "e.g., Paris,FR or London,UK"
                    },
                    "lat": {
                        "type": "number",
                        "label": "Latitude (optional)",
                        "placeholder": "e.g., 48.8566"
                    },
                    "lon": {
                        "type": "number",
                        "label": "Longitude (optional)",
                        "placeholder": "e.g., 2.3522"
                    },
                    "units": {
                        "type": "select",
                        "label": "Units",
                        "options": ["metric", "imperial", "standard"]
                    }
                },
            ),
            AutomationOption(
                key="get_forecast",
                name="Get Weather Forecast",
                description="Retrieve weather forecast for the next 5 days for a location.",
                params={
                    "location": {
                        "type": "text",
                        "label": "Location (City)",
                        "placeholder": "e.g., Tokyo,JP or Berlin,DE"
                    },
                    "lat": {
                        "type": "number",
                        "label": "Latitude (optional)",
                        "placeholder": "e.g., 35.6762"
                    },
                    "lon": {
                        "type": "number",
                        "label": "Longitude (optional)",
                        "placeholder": "e.g., 139.6503"
                    },
                    "units": {
                        "type": "select",
                        "label": "Units",
                        "options": ["metric", "imperial", "standard"]
                    },
                    "cnt": {
                        "type": "number",
                        "label": "Number of Forecasts (optional)",
                        "placeholder": "e.g., 8 (default: all available)"
                    }
                },
            ),
        ),
    ),
    ServiceIntegration(
        slug="openai",
        name="OpenAI",
        description="Leverage OpenAI's powerful models for text generation, chat, image creation, and content moderation.",
        actions=(
            AutomationOption(
                key="prompt",
                name="Text/Chat Completion Trigger",
                description="Triggers when certain conditions are met to generate text or chat responses.",
                params=None,
            ),
        ),
        reactions=(
            AutomationOption(
                key="complete_text",
                name="Generate Text Completion",
                description="Generate text completions from a prompt using OpenAI models.",
                params={
                    "prompt": {
                        "type": "text",
                        "label": "Prompt",
                        "placeholder": "Enter text to complete..."
                    },
                    "model": {
                        "type": "text",
                        "label": "Model (optional)",
                        "placeholder": "gpt-3.5-turbo-instruct",
                        "optional": True
                    },
                    "max_tokens": {
                        "type": "number",
                        "label": "Max Tokens (optional)",
                        "placeholder": "256",
                        "optional": True
                    }
                },
            ),
            AutomationOption(
                key="chat",
                name="Chat with GPT",
                description="Send a message to ChatGPT and get a response using OpenAI's chat models.",
                params={
                    "prompt": {
                        "type": "text",
                        "label": "Prompt",
                        "placeholder": "Enter your prompt (supports variables like {{gmail.subject}})"
                    },
                    "model": {
                        "type": "select",
                        "label": "Model (optional)",
                        "options": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
                        "optional": True
                    },
                    "max_tokens": {
                        "type": "number",
                        "label": "Max Tokens (optional)",
                        "placeholder": "500",
                        "optional": True
                    },
                    "temperature": {
                        "type": "number",
                        "label": "Temperature (optional)",
                        "placeholder": "0.7",
                        "optional": True
                    },
                    "system_prompt": {
                        "type": "text",
                        "label": "System Prompt (optional)",
                        "placeholder": "You are a helpful assistant...",
                        "optional": True
                    }
                },
            ),
            AutomationOption(
                key="generate_image",
                name="Create Image with DALL-E",
                description="Generate images from text descriptions using OpenAI's DALL-E model.",
                params={
                    "prompt": {
                        "type": "text",
                        "label": "Image Description",
                        "placeholder": "A cute cat playing with a ball of yarn..."
                    },
                    "size": {
                        "type": "select",
                        "label": "Image Size",
                        "options": ["256x256", "512x512", "1024x1024"],
                        "optional": True
                    },
                    "n": {
                        "type": "number",
                        "label": "Number of Images",
                        "placeholder": "1",
                        "optional": True
                    }
                },
            ),
            AutomationOption(
                key="analyze_text",
                name="Analyze/Moderate Content",
                description="Analyze content for potential policy violations using OpenAI's moderation API.",
                params={
                    "input": {
                        "type": "text",
                        "label": "Content to Moderate",
                        "placeholder": "Enter content to analyze (supports variables like {{gmail.body}})"
                    }
                },
            ),
        ),
    ),
    ServiceIntegration(
        slug="discord",
        name="Discord",
        description="Send messages and manage channels in Discord servers. Add the bot to your servers using the invite link.",
        actions=(
            AutomationOption(
                key="new_message_in_channel",
                name="New Message in Channel",
                description="Triggers when a new message is received in a specific Discord channel.",
                params={
                    "channel_id": {
                        "type": "text",
                        "label": "Channel ID",
                        "placeholder": "123456789012345678"
                    }
                },
            ),
            AutomationOption(
                key="reaction_added",
                name="Reaction Added to Message",
                description="Triggers when a user adds a reaction (emoji) to a specific Discord message.",
                params={
                    "channel_id": {
                        "type": "text",
                        "label": "Channel ID",
                        "placeholder": "123456789012345678"
                    },
                    "message_id": {
                        "type": "text",
                        "label": "Message ID",
                        "placeholder": "987654321098765432"
                    }
                },
            ),
        ),
        reactions=(
            AutomationOption(
                key="send_message",
                name="Send Message to Channel",
                description="Send a message to any Discord channel where the bot has been invited. Supports text, images, and videos via URL.",
                params={
                    "channel_id": {
                        "type": "text",
                        "label": "Channel ID",
                        "placeholder": "e.g., 123456789012345678"
                    },
                    "message": {
                        "type": "text",
                        "label": "Message",
                        "placeholder": "Enter message (supports variables like {{gmail.subject}})"
                    }
                },
            ),
            AutomationOption(
                key="create_channel",
                name="Create Channel",
                description="Create a new text or voice channel in any Discord server where the bot has been invited.",
                params={
                    "guild_id": {
                        "type": "text",
                        "label": "Server (Guild) ID",
                        "placeholder": "e.g., 123456789012345678"
                    },
                    "name": {
                        "type": "text",
                        "label": "Channel Name",
                        "placeholder": "e.g., new-announcements (supports variables)"
                    },
                    "type": {
                        "type": "select",
                        "label": "Channel Type",
                        "options": ["0", "2"]  # 0 = text, 2 = voice
                    }
                },
            ),
        ),
    ),
    ServiceIntegration(
        slug="google_calendar",
        name="Google Calendar",
        description="Automate workflows around calendar events, meetings, and schedules.",
        actions=(
            AutomationOption(
                key="event_created",
                name="Event Created",
                description="Triggers when a new event is added to the calendar.",
                params=None,
            ),
            AutomationOption(
                key="event_starting_soon",
                name="Event Starting Soon",
                description="Triggers X minutes before an event starts (configurable).",
                params={
                    "minutes": {
                        "type": "number",
                        "label": "Minutes Before Event",
                        "placeholder": "e.g., 10"
                    }
                },
            ),
        ),
        reactions=(
            AutomationOption(
                key="create_event",
                name="Create Event",
                description="Create a new calendar event with specified details.",
                params={
                    "summary": {
                        "type": "text",
                        "label": "Event Title",
                        "placeholder": "e.g., Team Meeting"
                    },
                    "location": {
                        "type": "text",
                        "label": "Location (optional)",
                        "placeholder": "e.g., Conference Room 1"
                    },
                    "description": {
                        "type": "text",
                        "label": "Description (optional)",
                        "placeholder": "Meeting agenda..."
                    },
                    "start_time": {
                        "type": "text",
                        "label": "Start Time",
                        "placeholder": "YYYY-MM-DDTHH:MM:SS (ISO 8601 format)"
                    },
                    "end_time": {
                        "type": "text",
                        "label": "End Time",
                        "placeholder": "YYYY-MM-DDTHH:MM:SS (ISO 8601 format)"
                    },
                    "attendees": {
                        "type": "text",
                        "label": "Attendees (optional, comma-separated)",
                        "placeholder": "user1@example.com, user2@example.com"
                    }
                },
            ),
            AutomationOption(
                key="update_event",
                name="Update Event",
                description="Modify an existing calendar event.",
                params={
                    "event_id": {
                        "type": "text",
                        "label": "Event ID",
                        "placeholder": "{{calendar.event_id}}"
                    },
                    "summary": {
                        "type": "text",
                        "label": "Event Title (optional)",
                        "placeholder": "e.g., Updated Team Meeting"
                    },
                    "location": {
                        "type": "text",
                        "label": "Location (optional)",
                        "placeholder": "e.g., New Conference Room"
                    },
                    "description": {
                        "type": "text",
                        "label": "Description (optional)",
                        "placeholder": "Updated meeting agenda..."
                    },
                    "start_time": {
                        "type": "text",
                        "label": "Start Time (optional)",
                        "placeholder": "YYYY-MM-DDTHH:MM:SS (ISO 8601 format)"
                    },
                    "end_time": {
                        "type": "text",
                        "label": "End Time (optional)",
                        "placeholder": "YYYY-MM-DDTHH:MM:SS (ISO 8601 format)"
                    }
                },
            ),
            AutomationOption(
                key="delete_event",
                name="Delete Event",
                description="Delete a calendar event.",
                params={
                    "event_id": {
                        "type": "text",
                        "label": "Event ID",
                        "placeholder": "{{calendar.event_id}}"
                    }
                },
            ),
            AutomationOption(
                key="create_all_day_event",
                name="Create All-Day Event",
                description="Create an all-day event (no specific time).",
                params={
                    "summary": {
                        "type": "text",
                        "label": "Event Title",
                        "placeholder": "e.g., Vacation Day"
                    },
                    "start_date": {
                        "type": "text",
                        "label": "Start Date",
                        "placeholder": "YYYY-MM-DD"
                    },
                    "end_date": {
                        "type": "text",
                        "label": "End Date (optional)",
                        "placeholder": "YYYY-MM-DD"
                    },
                    "description": {
                        "type": "text",
                        "label": "Description (optional)",
                        "placeholder": "Event details..."
                    }
                },
            ),
            AutomationOption(
                key="quick_add_event",
                name="Quick Add Event",
                description="Create an event using natural language (e.g., 'Meeting tomorrow at 3pm').",
                params={
                    "text": {
                        "type": "text",
                        "label": "Event Description",
                        "placeholder": "e.g., Meeting tomorrow at 3pm with John"
                    }
                },
            ),
        ),
    ),
    ServiceIntegration(
        slug="deepl",
        name="DeepL Translate",
        description="Professional translation service supporting 30+ languages with AI-powered accuracy.",
        actions=(),
        reactions=(
            AutomationOption(
                key="translate",
                name="Translate Text",
                description="Translate text from source language to target language.",
                outputs=(
                    "deepl.translated_text",
                    "deepl.source_language",
                    "deepl.target_language",
                    "deepl.detected_source_language",
                    "deepl.original_text",
                ),
            ),
            AutomationOption(
                key="auto_translate",
                name="Auto-Translate",
                description="Automatically detect source language and translate to target language.",
                outputs=(
                    "deepl.translated_text",
                    "deepl.detected_source_language",
                    "deepl.target_language",
                    "deepl.original_text",
                ),
            ),
            AutomationOption(
                key="detect_language",
                name="Detect Language",
                description="Detect the language of a text (uses small translation sample for detection).",
                outputs=(
                    "deepl.detected_language",
                    "deepl.original_text",
                    "deepl.sample_used",
                ),
            ),
        ),
    ),
)


def get_service_catalog() -> tuple[ServiceIntegration, ...]:
    """Return the immutable service catalog definition."""

    return SERVICE_CATALOG


def service_catalog_payload(simplified: bool = False) -> list[dict[str, object]]:
    """Return serialisable payload for API responses without mutating catalog data.
    
    Args:
        simplified: If True, returns spec-compliant format with only name/description fields.
                   If False (default), returns full catalog with all fields.
    """

    payload: list[dict[str, object]] = []
    for service in SERVICE_CATALOG:
        if simplified:
            # Spec-compliant format: name (identifier), actions, reactions
            # Per spec: name should be the identifier (key), not the human-readable name
            service_dict = {
                "name": service.slug,  # Use slug as the service identifier
                "actions": [
                    {"name": action.key, "description": action.description}
                    for action in service.actions
                ],
                "reactions": [
                    {"name": reaction.key, "description": reaction.description}
                    for reaction in service.reactions
                ],
            }
        else:
            # Full format with all fields (for internal API use)
            service_dict = asdict(service)
            service_dict["actions"] = [asdict(action) for action in service.actions]
            service_dict["reactions"] = [asdict(reaction) for reaction in service.reactions]

            # Convert tuple outputs to lists for JSON serialization consistency
            for action in service_dict["actions"]:
                if isinstance(action.get("outputs"), tuple):
                    action["outputs"] = list(action["outputs"])
            for reaction in service_dict["reactions"]:
                if isinstance(reaction.get("outputs"), tuple):
                    reaction["outputs"] = list(reaction["outputs"])

        payload.append(service_dict)
    return payload


__all__ = [
    "AutomationOption",
    "ServiceIntegration",
    "SERVICE_CATALOG",
    "get_service_catalog",
    "service_catalog_payload",
]
