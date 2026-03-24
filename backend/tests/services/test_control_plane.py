"""Tests for the control plane service and endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_create_session() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/control/sessions",
            json={"repo_url": "https://github.com/test/repo", "diff": "+ hello"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "session_token" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_session_status() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/control/sessions",
            json={"repo_url": "https://github.com/test/repo"},
        )
        session_id = create_resp.json()["session_id"]
        token = create_resp.json()["session_token"]

        resp = await client.get(
            f"/api/control/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_get_session_invalid_token() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/control/sessions",
            json={"repo_url": "https://github.com/test/repo"},
        )
        session_id = create_resp.json()["session_id"]

        resp = await client.get(
            f"/api/control/sessions/{session_id}",
            headers={"Authorization": "Bearer wrong-token"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_llm_proxy_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/control/llm",
            json={"session_id": "fake", "messages": []},
        )
    assert resp.status_code == 401
