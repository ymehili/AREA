"""Plugin registry for simple time-based triggers and debug reactions."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")

# Handler type: callable that takes (area, params, event) and returns None
PluginHandler = Callable[["Area", dict, dict], None]


class PluginsRegistry:
    """Registry mapping service/action pairs to handler functions."""

    def __init__(self) -> None:
        """Initialize the plugins registry with default handlers."""
        self._handlers: dict[tuple[str, str], PluginHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register built-in handlers for time and debug services."""
        # Time trigger doesn't need a handler (scheduler handles it)
        # Debug reaction handler
        self._handlers[("debug", "log")] = self._debug_log_handler

    @staticmethod
    def _debug_log_handler(area: Area, params: dict, event: dict) -> None:
        """Log a message with structured context.

        Args:
            area: The Area being executed
            params: reaction_params containing optional 'message' template
            event: Event data with 'now', 'area_id', 'user_id', 'tick'
        """
        # Get message template from params or use default
        message_template = params.get("message", "Area triggered at {{ now }}")

        # Simple template replacement
        message = message_template.replace("{{ now }}", event.get("now", ""))
        message = message.replace("{{ area.name }}", area.name)

        # Log with structured context
        logger.info(
            f"area_run area_id={str(area.id)} user_id={str(area.user_id)} "
            f"trigger={area.trigger_service}.{area.trigger_action} "
            f"reaction={area.reaction_service}.{area.reaction_action} "
            f"now={event.get('now')} message=\"{message}\""
        )

    def get_reaction_handler(
        self, service: str, action: str
    ) -> PluginHandler | None:
        """Get the reaction handler for a service/action pair.

        Args:
            service: Service slug (e.g., "debug")
            action: Action key (e.g., "log")

        Returns:
            Handler function or None if not found
        """
        return self._handlers.get((service, action))


# Global registry instance
_registry: PluginsRegistry | None = None


def get_plugins_registry() -> PluginsRegistry:
    """Get or create the global plugins registry instance."""
    global _registry
    if _registry is None:
        _registry = PluginsRegistry()
    return _registry


__all__ = ["PluginsRegistry", "get_plugins_registry"]