"""FastAPI application entrypoint."""

import logging
from datetime import datetime

from fastapi import FastAPI, Request

from app.core.config import settings
from app.db.session import verify_connection

app = FastAPI()

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
        "client": {
            "host": request.client.host
        },
        "server": {
            "current_time": datetime.now().isoformat()
        }
    }

@app.get("/")
async def root():
    return {"message": "Server is running"}
