"""Service-specific variable extraction functions."""

from typing import Dict, Any


def extract_gmail_variables(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract common variables from Gmail events.
    
    Args:
        trigger_data: Dictionary containing Gmail event data
        
    Returns:
        Dictionary mapping variable names to their values
    """
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
    
    return variables


def extract_google_drive_variables(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract common variables from Google Drive events.
    
    Args:
        trigger_data: Dictionary containing Google Drive event data
        
    Returns:
        Dictionary mapping variable names to their values
    """
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
    
    return variables


def extract_github_variables(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract common variables from GitHub events.
    
    Args:
        trigger_data: Dictionary containing GitHub event data
        
    Returns:
        Dictionary mapping variable names to their values
    """
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
    
    return variables