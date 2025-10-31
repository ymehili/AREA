"""FastAPI application entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
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
from slowapi.util import get_remote_address
from app.integrations.simple_plugins.gmail_scheduler import (
    start_gmail_scheduler,
    stop_gmail_scheduler,
    is_gmail_scheduler_running,
)
from app.integrations.simple_plugins.discord_scheduler import (
    start_discord_scheduler,
    stop_discord_scheduler,
    is_discord_scheduler_running,
)
from app.integrations.simple_plugins.weather_scheduler import (
    start_weather_scheduler,
    stop_weather_scheduler,
    is_weather_scheduler_running,
)
from app.integrations.simple_plugins.outlook_scheduler import (
    start_outlook_scheduler,
    stop_outlook_scheduler,
    is_outlook_scheduler_running,
)
from app.integrations.simple_plugins.github_scheduler import (
    start_github_scheduler,
    stop_github_scheduler,
    is_github_scheduler_running,
)
from app.integrations.simple_plugins.calendar_scheduler import (
    start_calendar_scheduler,
    stop_calendar_scheduler,
    is_calendar_scheduler_running,
)


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

        # Start the Gmail polling scheduler (non-blocking)
        logger.info("Startup: starting Gmail scheduler")
        start_gmail_scheduler()
        # Do not hard-fail app startup if Gmail scheduler validation is inconclusive
        try:
            await asyncio.sleep(0.1)
            if not is_gmail_scheduler_running():
                logger.warning("Startup: Gmail scheduler not running yet; continuing")
            else:
                logger.info("Startup: Gmail scheduler started successfully")
        except Exception:
            logger.warning("Startup: Unable to verify Gmail scheduler status; continuing")

        # Validate Discord bot token if Discord features are enabled
        from app.core.encryption import get_discord_bot_token
        bot_token = get_discord_bot_token()
        if any([settings.discord_client_id, settings.discord_client_secret, settings.discord_bot_token, settings.encrypted_discord_bot_token]):
            # Discord features are configured, check if bot token exists
            if not bot_token:
                logger.error("Discord bot token is required when Discord features are enabled. Set DISCORD_BOT_TOKEN or ENCRYPTED_DISCORD_BOT_TOKEN in .env file.")
                raise RuntimeError("Discord bot token not configured but Discord features are enabled")
            else:
                logger.info("Startup: Discord bot token validated successfully")
        
        # Start the Discord polling scheduler (non-blocking)
        logger.info("Startup: starting Discord scheduler")
        start_discord_scheduler()
        try:
            await asyncio.sleep(0.1)
            if not is_discord_scheduler_running():
                logger.warning("Startup: Discord scheduler not running yet; continuing")
            else:
                logger.info("Startup: Discord scheduler started successfully")
        except Exception:
            logger.warning("Startup: Unable to verify Discord scheduler status; continuing")

        # Start the Weather polling scheduler (non-blocking)
        logger.info("Startup: starting Weather scheduler")
        start_weather_scheduler()
        try:
            await asyncio.sleep(0.1)
            if not is_weather_scheduler_running():
                logger.warning("Startup: Weather scheduler not running yet; continuing")
            else:
                logger.info("Startup: Weather scheduler started successfully")
        except Exception:
            logger.warning("Startup: Unable to verify Weather scheduler status; continuing")

        # Start the Outlook polling scheduler (non-blocking)
        logger.info("Startup: starting Outlook scheduler")
        start_outlook_scheduler()
        # Do not hard-fail app startup if Outlook scheduler validation is inconclusive
        try:
            await asyncio.sleep(0.1)
            if not is_outlook_scheduler_running():
                logger.warning("Startup: Outlook scheduler not running yet; continuing")
            else:
                logger.info("Startup: Outlook scheduler started successfully")
        except Exception:
            logger.warning("Startup: Unable to verify Outlook scheduler status; continuing")

        # Start the GitHub polling scheduler (non-blocking)
        logger.info("Startup: starting GitHub scheduler")
        start_github_scheduler()
        try:
            await asyncio.sleep(0.1)
            if not is_github_scheduler_running():
                logger.warning("Startup: GitHub scheduler not running yet; continuing")
            else:
                logger.info("Startup: GitHub scheduler started successfully")
        except Exception:
            logger.warning("Startup: Unable to verify GitHub scheduler status; continuing")

        # Start the Google Calendar polling scheduler (non-blocking)
        logger.info("Startup: starting Calendar scheduler")
        start_calendar_scheduler()
        try:
            await asyncio.sleep(0.1)
            if not is_calendar_scheduler_running():
                logger.warning("Startup: Calendar scheduler not running yet; continuing")
            else:
                logger.info("Startup: Calendar scheduler started successfully")
        except Exception:
            logger.warning("Startup: Unable to verify Calendar scheduler status; continuing")
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

    logger.info("Shutdown: stopping Discord scheduler")
    stop_discord_scheduler()
    logger.info("Shutdown: Discord scheduler stopped")

    logger.info("Shutdown: stopping Weather scheduler")
    stop_weather_scheduler()
    logger.info("Shutdown: Weather scheduler stopped")

    logger.info("Shutdown: stopping Outlook scheduler")
    stop_outlook_scheduler()
    logger.info("Shutdown: Outlook scheduler stopped")

    logger.info("Shutdown: stopping GitHub scheduler")
    stop_github_scheduler()
    logger.info("Shutdown: GitHub scheduler stopped")

    logger.info("Shutdown: stopping Calendar scheduler")
    stop_calendar_scheduler()
    logger.info("Shutdown: Calendar scheduler stopped")





logger.info("Creating FastAPI application instance")
app = FastAPI(lifespan=lifespan)
logger.info("FastAPI application created")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Add SlowAPI middleware
app.add_middleware(SlowAPIMiddleware)

# Add exception handler for rate limit exceeded
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/about.json")
async def about(request: Request):
    """Return application info in spec-compliant format."""
    import time
    return {
        "client": {"host": request.client.host},
        "server": {
            "current_time": int(time.time()),
            "services": service_catalog_payload(simplified=True)
        },
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
