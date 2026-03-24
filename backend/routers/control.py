"""Control plane API endpoints — session management, LLM proxy, artifact storage."""

import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request, UploadFile
from fastapi.params import File, Form
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/control")


class CreateSessionRequest(BaseModel):
    """Request to create a new agent session."""

    repo_url: str = ""
    pr_number: int = 0
    diff: str = ""
    app_url: str = ""


class LLMProxyRequest(BaseModel):
    """Request to proxy an LLM call."""

    session_id: str
    messages: list[dict[str, str]]


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    request: Request,
) -> dict[str, Any]:
    """Create a new agent session."""
    cp = request.app.state.control_plane
    session_id, token = cp.create_session(
        repo_url=body.repo_url,
        pr_number=body.pr_number,
        diff=body.diff,
        app_url=body.app_url,
    )
    return {"session_id": session_id, "session_token": token, "status": "pending"}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    request: Request,
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    """Get session status."""
    cp = request.app.state.control_plane
    token = authorization.replace("Bearer ", "")
    if not cp.validate_token(session_id, token):
        raise HTTPException(status_code=401, detail="Invalid session token")

    session = cp.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "status": session.status.value,
        "actions": len(session.actions),
    }


@router.post("/llm")
async def proxy_llm(
    body: LLMProxyRequest,
    request: Request,
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    """Proxy an LLM call — sandbox sends messages, we call Claude with real API keys."""
    cp = request.app.state.control_plane
    token = authorization.replace("Bearer ", "")
    if not cp.validate_token(body.session_id, token):
        raise HTTPException(status_code=401, detail="Invalid session token")

    from config.settings import load_settings

    api_key = load_settings().anthropic_api_key
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    from anthropic import AsyncAnthropic
    from anthropic.types import MessageParam

    client = AsyncAnthropic(api_key=api_key)
    typed_messages: list[MessageParam] = [
        {"role": m["role"], "content": m["content"]}  # type: ignore[typeddict-item]
        for m in body.messages
    ]

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=typed_messages,
    )
    result = response.content[0].text  # type: ignore[union-attr]

    logger.info(
        "LLM proxy call",
        extra={"session_id": body.session_id, "length": len(result)},
    )
    return {"response": result}


@router.post("/artifacts")
async def upload_artifact(
    request: Request,
    file: Annotated[UploadFile, File()],
    session_id: Annotated[str, Form()],
    artifact_type: str = "file",
    authorization: str = Header(default=""),
) -> dict[str, Any]:
    """Upload an artifact from the sandbox."""
    cp = request.app.state.control_plane
    token = authorization.replace("Bearer ", "")
    if not cp.validate_token(session_id, token):
        raise HTTPException(status_code=401, detail="Invalid session token")

    artifact_dir = Path(f"/tmp/pr-videos/artifacts/{session_id}")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    file_path = artifact_dir / (file.filename or "artifact")
    content = await file.read()
    file_path.write_bytes(content)

    cp.store_artifact(session_id, str(file_path))
    logger.info(
        "Artifact uploaded",
        extra={
            "session_id": session_id,
            "type": artifact_type,
            "size": len(content),
        },
    )
    return {"url": str(file_path), "size": len(content)}
