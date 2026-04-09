"""Content fetcher service for extracting metadata from URLs."""

import asyncio
import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from bookmarks_organizer.models.responses import FetchedContent

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = ("http://", "https://")


class ContentFetcher:
    """Fetches and parses content from URLs concurrently."""

    def __init__(
        self,
        concurrency: int = 10,
        timeout: float = 5.0,
    ) -> None:
        """Initialize with specific configuration values."""
        self._concurrency = concurrency
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(concurrency)

    async def fetch_batch(self, urls: list[str]) -> list[FetchedContent]:
        """Fetch content for a batch of URLs concurrently."""
        async with httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
        ) as client:
            tasks = [self._fetch_one(client, url) for url in urls]
            return await asyncio.gather(*tasks)

    async def _fetch_one(self, client: httpx.AsyncClient, url: str) -> FetchedContent:
        """Fetch and parse a single URL."""
        if not url.startswith(_ALLOWED_SCHEMES):
            return FetchedContent(
                url=url,
                success=False,
                error="Invalid URL scheme",
            )

        async with self._semaphore:
            try:
                response = await client.get(url)
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    return FetchedContent(url=url, success=False)
                return self._parse_html(url, response.text)
            except httpx.TimeoutException:
                logger.debug("Timeout fetching %s", url)
                return FetchedContent(url=url, success=False)
            except (
                httpx.RequestError,
                httpx.HTTPStatusError,
            ) as exc:
                logger.debug("Error fetching %s: %s", url, exc)
                return FetchedContent(url=url, success=False)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Unexpected error fetching %s: %s",
                    url,
                    exc,
                )
                return FetchedContent(url=url, success=False)

    def _parse_html(self, url: str, html: str) -> FetchedContent:
        """Extract title, description, and body text from HTML."""
        soup = BeautifulSoup(html, "lxml")

        title = self._extract_title(soup)
        description = self._extract_description(soup)
        body_text = self._extract_body_text(soup)

        return FetchedContent(
            url=url,
            title=title,
            description=description,
            body_text=body_text,
            success=True,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        tag = soup.find("title")
        if tag and tag.string:
            return tag.string.strip()
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        return ""

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description."""
        meta: Any = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return str(meta["content"]).strip()
        og_desc: Any = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            return str(og_desc["content"]).strip()
        return ""

    def _extract_body_text(self, soup: BeautifulSoup) -> str:
        """Extract first 500 chars of visible body text."""
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        body = soup.find("body")
        if body:
            text = body.get_text(separator=" ", strip=True)
            return text[:500]
        return ""
