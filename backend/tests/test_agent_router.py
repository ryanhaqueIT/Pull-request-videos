"""Tests for the agent API endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_agent_run_accepts_request() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/agents/run",
            json={
                "url": "http://localhost:3000",
                "diff": "+ added button",
                "mode": "direct",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert "session_id" in data
    assert data["mode"] == "direct"


@pytest.mark.asyncio
async def test_agent_run_sandbox_mode() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/agents/run",
            json={
                "url": "http://localhost:3000",
                "mode": "sandbox",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "sandbox"
