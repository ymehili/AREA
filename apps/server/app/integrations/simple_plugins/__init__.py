"""Simple plugins package for time-based triggers and debug reactions."""

from app.integrations.simple_plugins.registry import (
    PluginsRegistry,
    get_plugins_registry,
)
from app.integrations.simple_plugins.scheduler import (
    start_scheduler,
    stop_scheduler,
    clear_last_run_state,
)

__all__ = [
    "PluginsRegistry",
    "get_plugins_registry",
    "start_scheduler",
    "stop_scheduler",
    "clear_last_run_state",
]
