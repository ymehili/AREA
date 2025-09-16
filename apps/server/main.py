"""FastAPI application entrypoint."""

import logging
from datetime import datetime

from fastapi import FastAPI, Request

from app.api.routes.services import router as services_router
from app.core.config import settings
from app.db.session import verify_connection
from app.integrations.catalog import service_catalog_payload

app = FastAPI()

app.include_router(services_router, prefix="/services")
app.include_router(services_router, prefix="/api/v1/services")

logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event() -> None:
    """Validate database connectivity before serving requests."""

    try:
        verify_connection()
        app.state.database_url = settings.database_url
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.error("Database connection failed: %s", exc)
        raise

@app.get("/about.json")
async def about(request: Request):
    return {
        "client": {"host": request.client.host},
        "server": {"current_time": datetime.now().isoformat()},
        "services": service_catalog_payload(),
    }

@app.get("/")
async def root():
    return {"message": "Server is running"}
