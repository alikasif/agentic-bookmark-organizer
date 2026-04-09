"""Integration tests for the bookmarks and content API endpoints."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


@pytest.mark.anyio
async def test_organize_dry_run() -> None:
    """POST /organize with dry_run=true returns proposed operations."""
    from bookmarks_organizer.api.dependencies import (
        get_ai_organizer,
        get_bookmark_builder,
        get_content_fetcher,
    )
    from bookmarks_organizer.main import create_app
    from bookmarks_organizer.models.responses import (
        FolderNode,
        OrganizeProposal,
    )
    from bookmarks_organizer.services.bookmark_builder import BookmarkBuilder

    app = create_app()

    mock_fetcher = MagicMock()
    mock_fetcher.fetch_batch = AsyncMock(return_value=[])

    mock_organizer = MagicMock()
    proposal_obj = OrganizeProposal(
        proposed_structure=FolderNode(name="root"),
        operations=[],
        warnings=[],
    )
    mock_organizer.organize = AsyncMock(return_value=proposal_obj)

    real_builder = BookmarkBuilder()

    app.dependency_overrides[get_content_fetcher] = lambda: mock_fetcher
    app.dependency_overrides[get_ai_organizer] = lambda: mock_organizer
    app.dependency_overrides[get_bookmark_builder] = lambda: real_builder

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/organize",
                json={
                    "bookmarks": [
                        {
                            "id": "1",
                            "title": "Python",
                            "url": "https://python.org",
                            "depth": 1,
                        }
                    ],
                    "dry_run": True,
                    "max_folders": 20,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert "proposed_structure" in data
    assert "operations" in data
    assert "stats" in data
    assert data["stats"]["total_bookmarks"] == 1


@pytest.mark.anyio
async def test_organize_invalid_request() -> None:
    """POST /organize with missing required fields returns 422."""
    from bookmarks_organizer.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/organize", json={})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_content_fetch_endpoint() -> None:
    """POST /content/fetch returns results."""
    from bookmarks_organizer.api.dependencies import get_content_fetcher
    from bookmarks_organizer.main import create_app
    from bookmarks_organizer.models.responses import FetchedContent

    app = create_app()
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_batch = AsyncMock(
        return_value=[
            FetchedContent(
                url="https://example.com",
                title="Example",
                description="A test",
                success=True,
            )
        ]
    )

    app.dependency_overrides[get_content_fetcher] = lambda: mock_fetcher

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/content/fetch",
                json={"urls": ["https://example.com"]},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["success"] is True


@pytest.mark.anyio
async def test_organize_server_error_hides_detail() -> None:
    """POST /organize returns generic error, not internal details."""
    from bookmarks_organizer.api.dependencies import (
        get_ai_organizer,
        get_bookmark_builder,
        get_content_fetcher,
    )
    from bookmarks_organizer.main import create_app

    app = create_app()

    mock_fetcher = MagicMock()
    mock_fetcher.fetch_batch = AsyncMock(
        side_effect=RuntimeError("secret internal detail")
    )

    app.dependency_overrides[get_content_fetcher] = lambda: mock_fetcher
    app.dependency_overrides[get_ai_organizer] = lambda: MagicMock()
    app.dependency_overrides[get_bookmark_builder] = lambda: MagicMock()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/organize",
                json={
                    "bookmarks": [
                        {
                            "id": "1",
                            "title": "Test",
                            "url": "https://test.com",
                            "depth": 1,
                        }
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert "secret internal detail" not in response.text
    assert response.json()["detail"] == "Internal server error"


@pytest.mark.anyio
async def test_content_fetch_server_error() -> None:
    """POST /content/fetch returns 500 on unexpected errors."""
    from bookmarks_organizer.api.dependencies import get_content_fetcher
    from bookmarks_organizer.main import create_app

    app = create_app()

    mock_fetcher = MagicMock()
    mock_fetcher.fetch_batch = AsyncMock(side_effect=RuntimeError("unexpected"))

    app.dependency_overrides[get_content_fetcher] = lambda: mock_fetcher

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/content/fetch",
                json={"urls": ["https://example.com"]},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
