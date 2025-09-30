"""FastAPI application entrypoint."""

import asyncio
import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.oauth import router as oauth_router
from app.api.routes.profile import router as profile_router
from app.api.routes.services import router as services_router
from app.api.routes.service_connections import router as service_connections_router
from app.api import areas_router
from app.api.routes.admin import router as admin_router
from app.core.config import settings
from app.db.migrations import run_migrations
from app.db.session import verify_connection
from app.integrations.catalog import service_catalog_payload
from app.integrations.simple_plugins.scheduler import start_scheduler, stop_scheduler


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Run migrations before creating the app (only in production or main dev process)
import sys
import os
# Only run migrations if we're not in test mode and not in a reloader subprocess
if (
    "pytest" not in sys.modules
    and "PYTEST_CURRENT_TEST" not in os.environ
):
    logger.info("Running migrations before app creation")
    try:
        run_migrations()
        logger.info("Migrations complete")
    except Exception as exc:
        logger.error("Migration failed", exc_info=True)
        # Continue anyway - migrations may already be applied

logger.info("Creating FastAPI application instance")
app = FastAPI()
logger.info("FastAPI application created")

# Add CORS middleware for development
logger.info("Configuring CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_redirect_url_web],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Session middleware for OAuth
logger.info("Configuring Session middleware for OAuth callbacks")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)


@app.on_event("startup")
async def startup_event() -> None:
    """Validate database connectivity and start scheduler."""

    try:
        logger.info("Startup: verifying database connection")
        verify_connection()
        logger.info("Startup: database connection verified")
        app.state.database_url = settings.database_url

        # Start the background scheduler for time-based areas
        logger.info("Startup: starting scheduler")
        start_scheduler()
        logger.info("Startup: scheduler started")
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.error("Startup failure", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on application shutdown."""
    logger.info("Shutdown: stopping scheduler")
    stop_scheduler()
    logger.info("Shutdown: scheduler stopped")


@app.get("/")
async def root():
    return {"message": "Server is running"}


@app.get("/about.json")
async def about(request: Request):
    return {
        "client": {"host": request.client.host},
        "server": {"current_time": datetime.now().isoformat()},
        "services": service_catalog_payload(),
    }

logger.info("Registering API routers")
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(oauth_router, prefix="/api/v1/oauth")
app.include_router(service_connections_router, prefix="/api/v1/service-connections")
app.include_router(profile_router, prefix="/api/v1/users")
app.include_router(services_router, prefix="/services")
app.include_router(services_router, prefix="/api/v1/services")
app.include_router(areas_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
logger.info("Routers registered; application ready to accept requests")
