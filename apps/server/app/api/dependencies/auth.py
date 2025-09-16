"""Authentication dependencies for API routes."""


def require_active_user() -> None:
    """Placeholder guard ensuring only active users access protected routes."""

    return None


__all__ = ["require_active_user"]

