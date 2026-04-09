"""Tests for ContentFetcher service."""

import os

import httpx
import pytest
import respx

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture
def fetcher():
    """Return a ContentFetcher instance."""
    from bookmarks_organizer.services.content_fetcher import ContentFetcher

    return ContentFetcher(concurrency=10, timeout=5.0)


@pytest.mark.anyio
async def test_fetch_success(fetcher) -> None:
    """Successfully fetches and parses HTML content."""
    html = (
        "<html><head>"
        "<title>Test Page</title>"
        "<meta name='description' content='A test'>"
        "</head><body><p>Hello world</p></body></html>"
    )
    with respx.mock:
        respx.get("https://example.com").mock(
            return_value=httpx.Response(
                200, text=html, headers={"content-type": "text/html"}
            )
        )
        results = await fetcher.fetch_batch(["https://example.com"])
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].title == "Test Page"
    assert results[0].description == "A test"


@pytest.mark.anyio
async def test_fetch_timeout(fetcher) -> None:
    """Returns failure on timeout."""
    with respx.mock:
        respx.get("https://slow.example.com").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        results = await fetcher.fetch_batch(["https://slow.example.com"])
    assert results[0].success is False


@pytest.mark.anyio
async def test_fetch_non_html(fetcher) -> None:
    """Returns failure for non-HTML content."""
    with respx.mock:
        respx.get("https://example.com/file.pdf").mock(
            return_value=httpx.Response(
                200,
                content=b"%PDF-1.4",
                headers={"content-type": "application/pdf"},
            )
        )
        results = await fetcher.fetch_batch(["https://example.com/file.pdf"])
    assert results[0].success is False


@pytest.mark.anyio
async def test_fetch_connection_error(fetcher) -> None:
    """Returns failure on connection error."""
    with respx.mock:
        respx.get("https://unreachable.example.com").mock(
            side_effect=httpx.ConnectError("failed")
        )
        results = await fetcher.fetch_batch(["https://unreachable.example.com"])
    assert results[0].success is False


@pytest.mark.anyio
async def test_fetch_empty_list(fetcher) -> None:
    """Returns empty list when given empty URL list."""
    results = await fetcher.fetch_batch([])
    assert results == []


@pytest.mark.anyio
async def test_fetch_invalid_scheme(fetcher) -> None:
    """Returns failure for non-HTTP/HTTPS URLs."""
    results = await fetcher.fetch_batch(["file:///etc/passwd"])
    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error == "Invalid URL scheme"


@pytest.mark.anyio
async def test_fetch_ftp_scheme(fetcher) -> None:
    """Returns failure for FTP URLs."""
    results = await fetcher.fetch_batch(["ftp://example.com/file"])
    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error == "Invalid URL scheme"
