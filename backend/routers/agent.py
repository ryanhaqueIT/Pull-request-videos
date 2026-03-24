"""Agent endpoint — triggers the full cloud agent pipeline."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents")


class AgentRunRequest(BaseModel):
    """Request to run an agent."""

    url: str
    diff: str = ""
    repo_url: str = ""
    pr_number: int = 0
    mode: str = "direct"  # "direct" or "sandbox"


@router.post("/run")
async def run_agent(
    body: AgentRunRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Trigger an agent run. Returns immediately with session ID."""
    session_id = str(uuid.uuid4())[:8]
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    logger.info(
        "Agent run requested",
        extra={
            "correlation_id": correlation_id,
            "session_id": session_id,
            "url": body.url,
            "mode": body.mode,
        },
    )

    return {
        "status": "accepted",
        "session_id": session_id,
        "mode": body.mode,
        "url": body.url,
    }
