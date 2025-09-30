"""SQLAlchemy declarative base for ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# Import model modules so SQLAlchemy registers the mappers during startup.
from app.models import (  # noqa: E402,F401
    email_verification_token,
    service_connection,
    user,
    area,
    area_step,
)


__all__ = ["Base"]
