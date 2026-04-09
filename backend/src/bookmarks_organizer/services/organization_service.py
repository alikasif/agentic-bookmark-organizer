"""Orchestration service for bookmark organization workflow."""

import logging

from bookmarks_organizer.models.requests import BookmarkItem
from bookmarks_organizer.models.responses import OrganizeResponse
from bookmarks_organizer.services.protocols import (
    AIOrganizerProtocol,
    BookmarkBuilderProtocol,
    ContentFetcherProtocol,
)

logger = logging.getLogger(__name__)


class OrganizationService:
    """Orchestrates the full bookmark organization workflow.

    Coordinates content fetching, enrichment, AI organization,
    and response building.
    """

    def __init__(
        self,
        content_fetcher: ContentFetcherProtocol,
        ai_organizer: AIOrganizerProtocol,
        bookmark_builder: BookmarkBuilderProtocol,
    ) -> None:
        """Initialize with injected service dependencies."""
        self._content_fetcher = content_fetcher
        self._ai_organizer = ai_organizer
        self._bookmark_builder = bookmark_builder

    async def organize(
        self,
        bookmarks: list[BookmarkItem],
        max_folders: int,
    ) -> OrganizeResponse:
        """Run the full organize workflow.

        Steps: fetch content -> enrich bookmarks -> AI organize
        -> build response.
        """
        urls = [bm.url for bm in bookmarks if bm.url]
        fetched = await self._content_fetcher.fetch_batch(urls) if urls else []

        enriched = self._bookmark_builder.enrich_bookmarks(bookmarks, fetched)
        proposal = await self._ai_organizer.organize(enriched, max_folders)
        return self._bookmark_builder.build_response(proposal, bookmarks)
