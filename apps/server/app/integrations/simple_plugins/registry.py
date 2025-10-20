"""Plugin registry for simple time-based triggers and debug reactions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")

# Handler type: callable that takes (area, params, event) and returns None or Awaitable[None]
PluginHandler = Callable[["Area", dict, dict], None | Awaitable[None]]


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

        # Delay handler
        from app.integrations.simple_plugins.delay_plugin import delay_handler
        self._handlers[("delay", "wait")] = delay_handler

        # Gmail handlers
        from app.integrations.simple_plugins.gmail_plugin import (
            send_email_handler,
            mark_as_read_handler,
            forward_email_handler,
        )
        self._handlers[("gmail", "send_email")] = send_email_handler
        self._handlers[("gmail", "mark_as_read")] = mark_as_read_handler
        self._handlers[("gmail", "forward_email")] = forward_email_handler

        # Weather handlers
        from app.integrations.simple_plugins.weather_plugin import (
            get_current_weather_handler,
            get_forecast_handler,
        )
        self._handlers[("weather", "get_current_weather")] = get_current_weather_handler
        self._handlers[("weather", "get_forecast")] = get_forecast_handler

        # OpenAI handlers
        from app.integrations.simple_plugins.openai_plugin import (
            chat_completion_handler,
            text_completion_handler,
            image_generation_handler,
            content_moderation_handler,
        )
        self._handlers[("openai", "chat")] = chat_completion_handler
        self._handlers[("openai", "complete_text")] = text_completion_handler
        self._handlers[("openai", "generate_image")] = image_generation_handler
        self._handlers[("openai", "analyze_text")] = content_moderation_handler

        # Discord handlers
        from app.integrations.simple_plugins.discord_plugin import (
            send_message_handler,
            create_channel_handler,
        )
        self._handlers[("discord", "send_message")] = send_message_handler
        self._handlers[("discord", "create_channel")] = create_channel_handler

    @staticmethod
    def _debug_log_handler(area: Area, params: dict, event: dict) -> None:
        """Log a message with structured context.

        Args:
            area: The Area being executed
            params: reaction_params containing optional 'message' template
            event: Event data with 'now', 'area_id', 'user_id', plus trigger-specific data
        """
        from app.services.variable_resolver import resolve_variables

        # Get message template from params or use default
        message_template = params.get("message", "Area triggered at {{ now }}")

        # Add area data to event for variable resolution
        event_with_area = {
            **event,
            "area.name": area.name,
            "area.id": str(area.id),
            "area.user_id": str(area.user_id),
        }

        # Use the variable resolver to replace all variables
        message = resolve_variables(message_template, event_with_area)

        # Log with structured context including all event data
        event_summary = {k: v for k, v in event.items() if k in ['now', 'gmail.sender', 'gmail.subject', 'gmail.snippet']}

        logger.info(
            f"area_run area_id={str(area.id)} user_id={str(area.user_id)} "
            f"trigger={area.trigger_service}.{area.trigger_action} "
            f"reaction={area.reaction_service}.{area.reaction_action} "
            f"now={event.get('now')} message=\"{message}\" event_data={event_summary}"
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