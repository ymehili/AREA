"""FastAPI application entrypoint."""

import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.services import router as services_router
from app.core.config import settings
from app.db.session import verify_connection
from app.integrations.catalog import service_catalog_payload


app = FastAPI()

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(services_router, prefix="/services")
app.include_router(services_router, prefix="/api/v1/services")
