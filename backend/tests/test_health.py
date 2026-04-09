"""Tests for health endpoint."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


@pytest.mark.anyio
async def test_health_returns_ok() -> None:
    """Health endpoint returns 200 with ok status."""
    from bookmarks_organizer.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
