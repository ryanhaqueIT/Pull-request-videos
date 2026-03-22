"""Video generation endpoint. Routers route — delegates to services."""

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos")


class GenerateRequest(BaseModel):
    """Request body for video generation."""

    url: str
    diff: str = ""


@router.post("/generate")
async def generate_video(body: GenerateRequest, request: Request) -> dict[str, Any]:
    """Trigger video generation for a URL."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.info(
        "Video generation requested",
        extra={"correlation_id": correlation_id, "url": body.url},
    )
    # Pipeline integration will be added in Milestone 4
    return {
        "status": "accepted",
        "url": body.url,
        "correlation_id": correlation_id,
    }
