"""Immutable catalog definitions for service actions and reactions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final, Sequence


@dataclass(frozen=True)
class AutomationOption:
    """A single automation option exposed by a third-party service."""

    key: str
    name: str
    description: str


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
        slug="gmail",
        name="Gmail",
        description="Automate workflows around incoming and outgoing email events.",
        actions=(
            AutomationOption(
                key="new_email",
                name="New Email Received",
                description="Triggers when a new email arrives in the inbox.",
            ),
            AutomationOption(
                key="email_starred",
                name="Email Starred",
                description="Triggers when a message is starred by the user.",
            ),
        ),
        reactions=(
            AutomationOption(
                key="send_email",
                name="Send Email",
                description="Send an email message to one or more recipients.",
            ),
            AutomationOption(
                key="create_label",
                name="Create Label",
                description="Create a new label inside the Gmail account.",
            ),
        ),
    ),
    ServiceIntegration(
        slug="google_drive",
        name="Google Drive",
        description="Manage files and folders stored in Google Drive.",
        actions=(
            AutomationOption(
                key="file_created",
                name="File Created",
                description="Triggers when a new file is added to the drive.",
            ),
            AutomationOption(
                key="file_deleted",
                name="File Deleted",
                description="Triggers when a file is deleted from the drive.",
            ),
        ),
        reactions=(
            AutomationOption(
                key="upload_file",
                name="Upload File",
                description="Upload a new file into a specified folder.",
            ),
            AutomationOption(
                key="create_folder",
                name="Create Folder",
                description="Create a folder at the root or within another folder.",
            ),
        ),
    ),
    ServiceIntegration(
        slug="dropbox",
        name="Dropbox",
        description="Keep Dropbox files in sync across automation flows.",
        actions=(
            AutomationOption(
                key="file_added",
                name="File Added",
                description="Triggers when a new file is added to Dropbox.",
            ),
            AutomationOption(
                key="folder_shared",
                name="Folder Shared",
                description="Triggers when a folder is shared with the user.",
            ),
        ),
        reactions=(
            AutomationOption(
                key="create_shared_link",
                name="Create Shared Link",
                description="Generate a new shareable link for a file or folder.",
            ),
            AutomationOption(
                key="upload_file",
                name="Upload File",
                description="Upload or replace a file in Dropbox storage.",
            ),
        ),
    ),
    ServiceIntegration(
        slug="slack",
        name="Slack",
        description="Coordinate messaging and channel notifications in Slack.",
        actions=(
            AutomationOption(
                key="message_posted",
                name="Message Posted",
                description="Triggers when a message is posted in a channel.",
            ),
            AutomationOption(
                key="reaction_added",
                name="Reaction Added",
                description="Triggers when a reaction is added to a message.",
            ),
        ),
        reactions=(
            AutomationOption(
                key="post_message",
                name="Post Message",
                description="Send a message to a channel or direct message.",
            ),
            AutomationOption(
                key="send_dm",
                name="Send Direct Message",
                description="Send a direct message to a specific user.",
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
            ),
            AutomationOption(
                key="new_issue",
                name="New Issue Created",
                description="Triggers when a new issue is created in a repository.",
            ),
            AutomationOption(
                key="pull_request_opened",
                name="Pull Request Opened",
                description="Triggers when a new pull request is opened.",
            ),
            AutomationOption(
                key="release_published",
                name="Release Published",
                description="Triggers when a new release is published.",
            ),
        ),
        reactions=(
            AutomationOption(
                key="create_issue",
                name="Create Issue",
                description="Create a new issue in a repository.",
            ),
            AutomationOption(
                key="add_comment",
                name="Add Comment",
                description="Add a comment to an issue or pull request.",
            ),
            AutomationOption(
                key="create_branch",
                name="Create Branch",
                description="Create a new branch in a repository.",
            ),
            AutomationOption(
                key="update_file",
                name="Update File",
                description="Update or create a file in a repository.",
            ),
        ),
    ),
)


def get_service_catalog() -> tuple[ServiceIntegration, ...]:
    """Return the immutable service catalog definition."""

    return SERVICE_CATALOG


def service_catalog_payload() -> list[dict[str, object]]:
    """Return serialisable payload for API responses without mutating catalog data."""

    payload: list[dict[str, object]] = []
    for service in SERVICE_CATALOG:
        service_dict = asdict(service)
        service_dict["actions"] = [asdict(action) for action in service.actions]
        service_dict["reactions"] = [asdict(reaction) for reaction in service.reactions]
        payload.append(service_dict)
    return payload


__all__ = [
    "AutomationOption",
    "ServiceIntegration",
    "SERVICE_CATALOG",
    "get_service_catalog",
    "service_catalog_payload",
]
