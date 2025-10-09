"""Service for extracting and substituting variables in step configurations."""

from typing import Dict, Any, List
import re

from app.integrations.variable_extractor import (
    extract_gmail_variables,
    extract_google_drive_variables,
    extract_github_variables,
)


def extract_variables_from_trigger_data(trigger_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key-value pairs from trigger event data.
    
    Args:
        trigger_data: Dictionary containing trigger event data
        
    Returns:
        Dictionary mapping variable names to their values
    """
    variables = {}
    
    def _extract_recursive(data, prefix=""):
        """Recursively extract key-value pairs from nested data."""
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                _extract_recursive(value, new_prefix)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_prefix = f"{prefix}.{i}" if prefix else str(i)
                _extract_recursive(item, new_prefix)
        else:
            # Add the variable with its path as key
            variables[prefix] = data
    
    _extract_recursive(trigger_data)
    return variables


def substitute_variables_in_params(params: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
    """Replace {{variable}} placeholders with actual values in parameters.
    
    Args:
        params: Dictionary containing parameters that may have variable placeholders
        variables: Dictionary of available variables to substitute
        
    Returns:
        Dictionary with variables substituted
    """
    import copy
    result = copy.deepcopy(params)
    
    def _substitute_recursive(obj):
        """Recursively substitute variables in nested objects."""
        if isinstance(obj, str):
            # Replace {{variable}} patterns with actual values
            pattern = r"\{\{(\w+(?:\.\w+)*)\}\}"  # Matches {{var}} or {{var.nested}}
            matches = re.findall(pattern, obj)
            for match in matches:
                if match in variables:
                    # Replace the variable with its value
                    # Handle different value types appropriately
                    var_value = variables[match]
                    
                    # If it's the entire string, replace with the actual value (not string)
                    if obj == f"{{{{{match}}}}}":
                        return var_value
                    else:
                        # Otherwise, convert to string for partial replacement
                        obj = obj.replace(f"{{{{{match}}}}}", str(var_value))
            return obj
        elif isinstance(obj, dict):
            return {key: _substitute_recursive(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [_substitute_recursive(item) for item in obj]
        else:
            return obj
    
    return _substitute_recursive(result)


def resolve_variables(template: str, variables: Dict[str, Any]) -> str:
    """Substitute {{var}} placeholders inside a string template using provided variables.

    Supports dotted paths like {{gmail.subject}}. If a variable is missing,
    it is left unchanged in the template.

    Args:
        template: The string containing placeholders.
        variables: Mapping of variable names to values.

    Returns:
        The template with placeholders replaced.
    """
    if not isinstance(template, str):
        return template  # type: ignore[return-value]

    pattern = r"\{\{\s*(\w+(?:\.\w+)*)\s*\}\}"

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in variables:
            value = variables[key]
            return str(value)
        return match.group(0)

    return re.sub(pattern, replace, template)

def get_available_variables_for_service(service_id: str, action_id: str) -> List[str]:
    """Get list of variables available for a service/action.
    
    Args:
        service_id: ID of the service
        action_id: ID of the action
        
    Returns:
        List of available variable names
    """
    # This function will be expanded to return service-specific variables
    # For now, return a general list of common variables
    common_variables = [
        "now",
        "timestamp",
        "utc.isoformat",
        "trigger",
        "user.id",
        "area.id"
    ]
    
    # Add service-specific variables based on the service
    service_specific = {
        "gmail": [
            "gmail.sender",
            "gmail.subject",
            "gmail.body",
            "gmail.attachments",
            "gmail.timestamp"
        ],
        "google_drive": [
            "drive.file_id",
            "drive.file_name",
            "drive.file_url",
            "drive.mime_type",
            "drive.owner",
            "drive.created_time",
            "drive.modified_time"
        ],
        "github": [
            "github.repo",
            "github.owner",
            "github.issue_number",
            "github.issue_title",
            "github.issue_body",
            "github.issue_author",
            "github.pull_request_number",
            "github.pull_request_title"
        ]
    }
    
    variables = common_variables[:]
    if service_id in service_specific:
        variables.extend(service_specific[service_id])
    
    return variables


def extract_variables_by_service(trigger_data: Dict[str, Any], service_type: str) -> Dict[str, Any]:
    """Extract variables using service-specific extractor based on service type.
    
    Args:
        trigger_data: Dictionary containing trigger event data
        service_type: Type of service (e.g., 'gmail', 'google_drive', 'github')
        
    Returns:
        Dictionary mapping variable names to their values
    """
    # If trigger_data already contains namespaced variables (e.g., "gmail.subject"),
    # pass them through directly. This happens when the trigger populated flat variables.
    if any(isinstance(k, str) and '.' in k for k in trigger_data.keys()):
        # Only include primitive or JSON-serializable values
        result: Dict[str, Any] = {}
        for k, v in trigger_data.items():
            if isinstance(k, str) and '.' in k:
                result[k] = v
        # Also pass common fields if present
        for k in ("now", "timestamp", "area_id", "user_id"):
            if k in trigger_data:
                result[k] = trigger_data[k]
        return result

    # Map service types to their specific extractors
    service_extractors = {
        'gmail': extract_gmail_variables,
        'google_drive': extract_google_drive_variables,
        'github': extract_github_variables
    }
    
    # Use service-specific extractor if available, otherwise use generic one
    if service_type in service_extractors:
        return service_extractors[service_type](trigger_data)
    else:
        # Fall back to generic extractor for unknown service types
        return extract_variables_from_trigger_data(trigger_data)