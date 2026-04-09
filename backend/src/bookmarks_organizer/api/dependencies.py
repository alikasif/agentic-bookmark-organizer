"""FastAPI dependency injection providers."""

from bookmarks_organizer.config import get_settings
from bookmarks_organizer.services.ai_organizer import AIOrganizer
from bookmarks_organizer.services.bookmark_builder import BookmarkBuilder
from bookmarks_organizer.services.content_fetcher import ContentFetcher
from bookmarks_organizer.services.protocols import (
    AIOrganizerProtocol,
    BookmarkBuilderProtocol,
    ContentFetcherProtocol,
)


def get_content_fetcher() -> ContentFetcherProtocol:
    """Provide a ContentFetcher instance."""
    settings = get_settings()
    return ContentFetcher(
        concurrency=settings.fetch_concurrency,
        timeout=settings.fetch_timeout_seconds,
    )


def get_ai_organizer() -> AIOrganizerProtocol:
    """Provide an AIOrganizer instance."""
    settings = get_settings()
    return AIOrganizer(
        api_key=settings.openrouter_api_key,
        model=settings.ai_model,
        base_url=settings.ai_base_url,
        batch_size=settings.ai_batch_size,
    )


def get_bookmark_builder() -> BookmarkBuilderProtocol:
    """Provide a BookmarkBuilder instance."""
    return BookmarkBuilder()
