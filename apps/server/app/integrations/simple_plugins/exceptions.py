"""Exceptions for simple plugin integrations."""

from __future__ import annotations


class GmailError(Exception):
    """Base exception for Gmail operations."""

    pass


class GmailAuthError(GmailError):
    """Gmail authentication/authorization failed."""

    pass


class GmailAPIError(GmailError):
    """Gmail API request failed."""

    pass


class GmailConnectionError(GmailError):
    """Gmail service connection not found or invalid."""

    pass


class OutlookError(Exception):
    """Base exception for Outlook operations."""

    pass


class OutlookAuthError(OutlookError):
    """Outlook authentication/authorization failed."""

    pass


class OutlookAPIError(OutlookError):
    """Outlook API request failed."""

    pass


class OutlookConnectionError(OutlookError):
    """Outlook service connection not found or invalid."""

    pass


class WeatherError(Exception):
    """Base exception for Weather operations."""

    pass


class WeatherAPIError(WeatherError):
    """Weather API request failed."""

    pass


class WeatherConfigError(WeatherError):
    """Weather configuration invalid or missing."""

    pass


class OpenAIError(Exception):
    """Base exception for OpenAI operations."""

    pass


class OpenAIAuthError(OpenAIError):
    """OpenAI authentication/authorization failed."""

    pass


class OpenAIAPIError(OpenAIError):
    """OpenAI API request failed."""

    pass


class OpenAIConnectionError(OpenAIError):
    """OpenAI service connection not found or invalid."""

    pass


class OpenAIConfigError(OpenAIError):
    """OpenAI configuration invalid or missing."""

    pass


class GitHubError(Exception):
    """Base exception for GitHub operations."""

    pass


class GitHubAuthError(GitHubError):
    """GitHub authentication/authorization failed."""

    pass


class GitHubAPIError(GitHubError):
    """GitHub API request failed."""

    pass


class GitHubConnectionError(GitHubError):
    """GitHub service connection not found or invalid."""

    pass


class CalendarError(Exception):
    """Base exception for Calendar operations."""

    pass


class CalendarAuthError(CalendarError):
    """Calendar authentication/authorization failed."""

    pass


class CalendarAPIError(CalendarError):
    """Calendar API request failed."""

    pass


class CalendarConnectionError(CalendarError):
    """Calendar service connection not found or invalid."""

    pass


class GoogleDriveError(Exception):
    """Base exception for Google Drive operations."""

    pass


class DeepLError(Exception):
    """Base exception for DeepL operations."""

    pass


class GoogleDriveAuthError(GoogleDriveError):
    """Google Drive authentication/authorization failed."""

    pass


class DeepLAuthError(DeepLError):
    """DeepL authentication failed (invalid API key)."""

    pass


class GoogleDriveAPIError(GoogleDriveError):
    """Google Drive API request failed."""

    pass


class DeepLAPIError(DeepLError):
    """DeepL API request failed."""

    pass


class GoogleDriveConnectionError(GoogleDriveError):
    """Google Drive service connection not found or invalid."""

    pass


class DeepLConfigError(DeepLError):
    """DeepL configuration invalid or missing."""

    pass


class DeepLConnectionError(DeepLError):
    """DeepL service connection not found or invalid."""

    pass


__all__ = [
    "GmailError",
    "GmailAuthError",
    "GmailAPIError",
    "GmailConnectionError",
    "OutlookError",
    "OutlookAuthError",
    "OutlookAPIError",
    "OutlookConnectionError",
    "WeatherError",
    "WeatherAPIError",
    "WeatherConfigError",
    "OpenAIError",
    "OpenAIAuthError",
    "OpenAIAPIError",
    "OpenAIConnectionError",
    "OpenAIConfigError",
    "GitHubError",
    "GitHubAuthError",
    "GitHubAPIError",
    "GitHubConnectionError",
    "CalendarError",
    "CalendarAuthError",
    "CalendarAPIError",
    "CalendarConnectionError",
    "GoogleDriveError",
    "GoogleDriveAuthError",
    "GoogleDriveAPIError",
    "GoogleDriveConnectionError",
    "DeepLError",
    "DeepLAuthError",
    "DeepLAPIError",
    "DeepLConfigError",
    "DeepLConnectionError",
]
