"""Tests for the health endpoint — behavior tests, not implementation tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    """GET /health returns HTTP 200."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_format(client: AsyncClient) -> None:
    """GET /health returns {"status": "healthy"}."""
    response = await client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_includes_correlation_id_header(client: AsyncClient) -> None:
    """Health response includes X-Correlation-ID header."""
    response = await client.get("/health")
    assert "x-correlation-id" in response.headers


@pytest.mark.asyncio
async def test_not_found_returns_structured_error(client: AsyncClient) -> None:
    """Unknown path returns 404 with correlation_id in body."""
    response = await client.get("/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "correlation_id" in data
    assert "error" in data
