"""Content fetching endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from bookmarks_organizer.api.dependencies import (
    get_content_fetcher,
)
from bookmarks_organizer.models.requests import ContentFetchRequest
from bookmarks_organizer.models.responses import ContentFetchResponse
from bookmarks_organizer.services.protocols import (
    ContentFetcherProtocol,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/content/fetch", response_model=ContentFetchResponse)
async def fetch_content(
    request: ContentFetchRequest,
    fetcher: ContentFetcherProtocol = Depends(get_content_fetcher),
) -> ContentFetchResponse:
    """Fetch metadata content from a list of URLs."""
    try:
        results = await fetcher.fetch_batch(request.urls)
        return ContentFetchResponse(results=results)
    except Exception:
        logger.exception("Error fetching content")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        ) from None
