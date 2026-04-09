"""Service protocols (interfaces) for dependency injection."""

from typing import Protocol

from bookmarks_organizer.models.requests import BookmarkItem
from bookmarks_organizer.models.responses import (
    BookmarkWithContent,
    FetchedContent,
    OrganizeProposal,
    OrganizeResponse,
)


class ContentFetcherProtocol(Protocol):
    """Protocol for fetching content from URLs."""

    async def fetch_batch(self, urls: list[str]) -> list[FetchedContent]:
        """Fetch content for a batch of URLs."""
        ...


class AIOrganizerProtocol(Protocol):
    """Protocol for AI-based bookmark organization."""

    async def organize(
        self,
        bookmarks: list[BookmarkWithContent],
        max_folders: int = 20,
    ) -> OrganizeProposal:
        """Organize bookmarks using AI."""
        ...


class BookmarkBuilderProtocol(Protocol):
    """Protocol for building bookmark operations from proposals."""

    def build_response(
        self,
        proposal: OrganizeProposal,
        original_bookmarks: list[BookmarkItem],
    ) -> OrganizeResponse:
        """Build an OrganizeResponse from a proposal."""
        ...

    def enrich_bookmarks(
        self,
        bookmarks: list[BookmarkItem],
        fetched: list[FetchedContent],
    ) -> list[BookmarkWithContent]:
        """Merge bookmark items with fetched content."""
        ...
