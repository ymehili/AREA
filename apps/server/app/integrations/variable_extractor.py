"""Service-specific variable extraction functions."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def extract_gmail_variables(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract common variables from Gmail events.
    
    Args:
        trigger_data: Dictionary containing Gmail event data
        
    Returns:
        Dictionary mapping variable names to their values
    """
    if not trigger_data:
        logger.warning("extract_gmail_variables called with empty trigger_data")
        return {}

    variables = {}
    
    # Extract common Gmail variables
    if 'payload' in trigger_data:
        payload = trigger_data['payload']
        
        # Extract headers
        if 'headers' in payload:
            headers = payload['headers']
            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '')
                
                if name == 'from':
                    variables['gmail.sender'] = value
                elif name == 'subject':
                    variables['gmail.subject'] = value
                elif name == 'date':
                    variables['gmail.timestamp'] = value
    
    # Extract body content if available
    if 'snippet' in trigger_data:
        variables['gmail.snippet'] = trigger_data['snippet']
    
    if 'body' in trigger_data:
        variables['gmail.body'] = trigger_data['body']
    
    # Extract other common fields
    if 'id' in trigger_data:
        variables['gmail.message_id'] = trigger_data['id']
        
    if 'threadId' in trigger_data:
        variables['gmail.thread_id'] = trigger_data['threadId']
    
    # Extract attachments if available
    if 'attachments' in trigger_data:
        variables['gmail.attachments'] = trigger_data['attachments']
    
    if not variables:
        logger.info("No Gmail variables extracted from trigger_data", extra={"trigger_data": trigger_data})

    return variables


def extract_google_drive_variables(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract common variables from Google Drive events.
    
    Args:
        trigger_data: Dictionary containing Google Drive event data
        
    Returns:
        Dictionary mapping variable names to their values
    """
    if not trigger_data:
        logger.warning("extract_google_drive_variables called with empty trigger_data")
        return {}

    variables = {}
    
    # Extract common Drive variables
    if 'fileId' in trigger_data:
        variables['drive.file_id'] = trigger_data['fileId']
    
    if 'id' in trigger_data:
        variables['drive.file_id'] = trigger_data['id']  # Alternative field name
        
    if 'name' in trigger_data:
        variables['drive.file_name'] = trigger_data['name']
        
    if 'mimeType' in trigger_data:
        variables['drive.mime_type'] = trigger_data['mimeType']
        
    if 'owners' in trigger_data and len(trigger_data['owners']) > 0:
        variables['drive.owner'] = trigger_data['owners'][0].get('emailAddress', '')
        
    if 'webViewLink' in trigger_data:
        variables['drive.file_url'] = trigger_data['webViewLink']
        
    if 'createdTime' in trigger_data:
        variables['drive.created_time'] = trigger_data['createdTime']
        
    if 'modifiedTime' in trigger_data:
        variables['drive.modified_time'] = trigger_data['modifiedTime']
        
    if 'size' in trigger_data:
        variables['drive.file_size'] = trigger_data['size']
        
    if 'description' in trigger_data:
        variables['drive.description'] = trigger_data['description']
    
    if not variables:
        logger.info("No Google Drive variables extracted from trigger_data", extra={"trigger_data": trigger_data})

    return variables


def extract_calendar_variables(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract common variables from Google Calendar events.

    Args:
        trigger_data: Dictionary containing Calendar event data

    Returns:
        Dictionary mapping variable names to their values
    """
    if not trigger_data:
        logger.warning("extract_calendar_variables called with empty trigger_data")
        return {}

    variables = {}

    # Extract common Calendar variables
    if 'id' in trigger_data:
        variables['calendar.event_id'] = trigger_data['id']

    if 'summary' in trigger_data:
        variables['calendar.title'] = trigger_data['summary']
        variables['calendar.summary'] = trigger_data['summary']

    if 'description' in trigger_data:
        variables['calendar.description'] = trigger_data['description']

    if 'location' in trigger_data:
        variables['calendar.location'] = trigger_data['location']

    if 'start_time' in trigger_data:
        variables['calendar.start_time'] = trigger_data['start_time']

    if 'end_time' in trigger_data:
        variables['calendar.end_time'] = trigger_data['end_time']

    if 'timezone' in trigger_data:
        variables['calendar.timezone'] = trigger_data['timezone']

    if 'attendees' in trigger_data:
        # Convert list to comma-separated string for easy use in templates
        if isinstance(trigger_data['attendees'], list):
            variables['calendar.attendees'] = ', '.join(trigger_data['attendees'])
        else:
            variables['calendar.attendees'] = trigger_data['attendees']

    if 'organizer' in trigger_data:
        variables['calendar.organizer'] = trigger_data['organizer']

    if 'status' in trigger_data:
        variables['calendar.status'] = trigger_data['status']

    if 'html_link' in trigger_data:
        variables['calendar.link'] = trigger_data['html_link']
        variables['calendar.html_link'] = trigger_data['html_link']

    if 'created' in trigger_data:
        variables['calendar.created'] = trigger_data['created']

    if 'updated' in trigger_data:
        variables['calendar.updated'] = trigger_data['updated']

    if 'is_all_day' in trigger_data:
        variables['calendar.is_all_day'] = str(trigger_data['is_all_day'])

    if not variables:
        logger.info("No Calendar variables extracted from trigger_data", extra={"trigger_data": trigger_data})

    return variables


def extract_github_variables(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract common variables from GitHub events.
    
    Args:
        trigger_data: Dictionary containing GitHub event data
        
    Returns:
        Dictionary mapping variable names to their values
    """
    if not trigger_data:
        logger.warning("extract_github_variables called with empty trigger_data")
        return {}

    variables = {}
    
    # Extract common GitHub variables
    if 'repository' in trigger_data:
        repo = trigger_data['repository']
        variables['github.repo'] = repo.get('name', '')
        variables['github.repo_full_name'] = repo.get('full_name', '')
        variables['github.repo_url'] = repo.get('html_url', '')
    
    if 'sender' in trigger_data:
        sender = trigger_data['sender']
        variables['github.sender'] = sender.get('login', '')
        variables['github.sender_avatar'] = sender.get('avatar_url', '')
        
    # Extract issue-related variables
    if 'issue' in trigger_data:
        issue = trigger_data['issue']
        variables['github.issue_number'] = issue.get('number', '')
        variables['github.issue_title'] = issue.get('title', '')
        variables['github.issue_body'] = issue.get('body', '')
        if 'user' in issue:
            variables['github.issue_author'] = issue['user'].get('login', '')
    
    # Extract pull request related variables
    if 'pull_request' in trigger_data:
        pr = trigger_data['pull_request']
        variables['github.pull_request_number'] = pr.get('number', '')
        variables['github.pull_request_title'] = pr.get('title', '')
        variables['github.pull_request_body'] = pr.get('body', '')
        if 'user' in pr:
            variables['github.pull_request_author'] = pr['user'].get('login', '')
    
    # Extract general event information
    if 'action' in trigger_data:
        variables['github.action'] = trigger_data['action']
    
    # Different event types have different structures
    if 'comment' in trigger_data:
        comment = trigger_data['comment']
        variables['github.comment_body'] = comment.get('body', '')
        if 'user' in comment:
            variables['github.comment_author'] = comment['user'].get('login', '')
    
    # For push events
    if 'commits' in trigger_data:
        variables['github.commits'] = trigger_data['commits']
        
    if 'ref' in trigger_data:
        variables['github.branch'] = trigger_data['ref'].replace("refs/heads/", "")
    
    if not variables:
        logger.info("No GitHub variables extracted from trigger_data", extra={"trigger_data": trigger_data})

    return variables
