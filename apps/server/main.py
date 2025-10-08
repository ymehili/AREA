"""FastAPI application entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.oauth import router as oauth_router
from app.api.routes.profile import router as profile_router
from app.api.routes.services import router as services_router
from app.api.routes.service_connections import router as service_connections_router
from app.api import areas_router, execution_logs_router
from app.api.routes.admin import router as admin_router
from app.api.routes.user_activity_logs import router as user_activity_log_router
from app.core.config import settings
from app.db.migrations import run_migrations
from app.db.session import verify_connection
from app.integrations.catalog import service_catalog_payload
from app.integrations.simple_plugins.scheduler import start_scheduler, stop_scheduler
from app.integrations.simple_plugins.gmail_scheduler import start_gmail_scheduler, stop_gmail_scheduler


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    try:
        logger.info("Startup: verifying database connection")
        # Verify database connection with retry logic
        verify_connection()
        logger.info("Startup: database connection verified")
        app.state.database_url = settings.database_url
        
        # Run migrations after database connection is verified but before starting the scheduler
        logger.info("Startup: running database migrations")
        try:
            run_migrations()
            logger.info("Startup: migrations completed")
        except Exception as migration_exc:
            logger.error("Startup: migration failed", exc_info=True)
            raise migration_exc

        # Start the background scheduler for time-based areas
        logger.info("Startup: starting scheduler")
        start_scheduler()
        logger.info("Startup: scheduler started")

        # Start the Gmail polling scheduler
        logger.info("Startup: starting Gmail scheduler")
        start_gmail_scheduler()
        logger.info("Startup: Gmail scheduler started")
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.error("Startup failure", exc_info=True)
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("Shutdown: stopping scheduler")
    stop_scheduler()
    logger.info("Shutdown: scheduler stopped")

    logger.info("Shutdown: stopping Gmail scheduler")
    stop_gmail_scheduler()
    logger.info("Shutdown: Gmail scheduler stopped")





logger.info("Creating FastAPI application instance")
app = FastAPI(lifespan=lifespan)
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
app.include_router(execution_logs_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(user_activity_log_router, prefix="/api/v1")
logger.info("Routers registered; application ready to accept requests")
