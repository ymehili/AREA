"""Database session and engine helpers."""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import time
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependencies."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_sync() -> Generator[Session, None, None]:
    """Yield a synchronous database session for CLI commands."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_connection(max_attempts: int = 20, delay_seconds: float = 1.0) -> None:
    """Ensure the database connection is reachable with simple retries.

    Args:
        max_attempts: Maximum number of attempts before failing.
        delay_seconds: Base delay between attempts; will use linear backoff.
    """

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            if attempt > 1:
                logger.info(
                    "Database connection established after %d attempt(s)", attempt
                )
            return
        except SQLAlchemyError as exc:
            last_exc = exc
            logger.warning(
                "Database not ready (attempt %d/%d): %s",
                attempt,
                max_attempts,
                type(exc).__name__,
            )
            time.sleep(delay_seconds * attempt)  # linear backoff

    logger.error(
        "Database connection verification failed after %d attempts",
        max_attempts,
        exc_info=last_exc,
    )
    raise (
        last_exc
        if last_exc
        else RuntimeError("Database connection verification failed")
    )


__all__ = ["engine", "SessionLocal", "get_db", "get_db_sync", "verify_connection"]
