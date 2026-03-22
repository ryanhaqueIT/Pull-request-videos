"""Health check endpoint. Routers route — no business logic here."""

import logging
from typing import Any

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    """Return service health status."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.info("Health check requested", extra={"correlation_id": correlation_id})
    return {"status": "healthy"}
