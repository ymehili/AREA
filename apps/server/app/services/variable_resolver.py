"""Service for extracting and substituting variables in step configurations."""

from typing import Dict, Any, List
import re


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