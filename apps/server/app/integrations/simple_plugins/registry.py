"""Plugin registry for simple time-based triggers and debug reactions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")

# Handler type: callable that takes (area, params, event, db) and returns None or Awaitable[None]
# db parameter is optional for backward compatibility but recommended for all new handlers
PluginHandler = Callable[..., None | Awaitable[None]]


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

        # Outlook handlers
        from app.integrations.simple_plugins.outlook_plugin import (
            send_email_handler as outlook_send_email,
            mark_as_read_handler as outlook_mark_as_read,
            forward_email_handler as outlook_forward_email,
        )
        self._handlers[("outlook", "send_email")] = outlook_send_email
        self._handlers[("outlook", "mark_as_read")] = outlook_mark_as_read
        self._handlers[("outlook", "forward_email")] = outlook_forward_email

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

        # GitHub handlers
        from app.integrations.simple_plugins.github_plugin import (
            create_issue_handler,
            add_comment_handler,
            close_issue_handler,
            add_label_handler,
            create_branch_handler,
        )
        self._handlers[("github", "create_issue")] = create_issue_handler
        self._handlers[("github", "add_comment")] = add_comment_handler
        self._handlers[("github", "close_issue")] = close_issue_handler
        self._handlers[("github", "add_label")] = add_label_handler
        self._handlers[("github", "create_branch")] = create_branch_handler

        # Google Calendar handlers
        from app.integrations.simple_plugins.calendar_plugin import (
            create_event_handler,
            update_event_handler,
            delete_event_handler,
            create_all_day_event_handler,
            quick_add_event_handler,
        )
        self._handlers[("google_calendar", "create_event")] = create_event_handler
        self._handlers[("google_calendar", "update_event")] = update_event_handler
        self._handlers[("google_calendar", "delete_event")] = delete_event_handler
        self._handlers[("google_calendar", "create_all_day_event")] = create_all_day_event_handler
        self._handlers[("google_calendar", "quick_add_event")] = quick_add_event_handler

        # DeepL handlers
        from app.integrations.simple_plugins.deepl_plugin import (
            translate_text_handler,
            auto_translate_handler,
            detect_language_handler,
        )
        self._handlers[("deepl", "translate")] = translate_text_handler
        self._handlers[("deepl", "auto_translate")] = auto_translate_handler
        self._handlers[("deepl", "detect_language")] = detect_language_handler

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

        # Log available variables for debugging
        logger.info(
            "Debug handler - available variables",
            extra={
                "area_id": str(area.id),
                "message_template": message_template,
                "event_keys": list(event.keys()),
                "event_with_area_keys": list(event_with_area.keys()),
                "deepl_detected_language": event_with_area.get("deepl.detected_language", "NOT_FOUND"),
                "deepl_detected_source_language": event_with_area.get("deepl.detected_source_language", "NOT_FOUND"),
            },
        )

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