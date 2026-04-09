"""Bookmark organization endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from bookmarks_organizer.api.dependencies import (
    get_ai_organizer,
    get_bookmark_builder,
    get_content_fetcher,
)
from bookmarks_organizer.models.requests import OrganizeRequest
from bookmarks_organizer.models.responses import OrganizeResponse
from bookmarks_organizer.services.organization_service import (
    OrganizationService,
)
from bookmarks_organizer.services.protocols import (
    AIOrganizerProtocol,
    BookmarkBuilderProtocol,
    ContentFetcherProtocol,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/organize", response_model=OrganizeResponse)
async def organize_bookmarks(
    request: OrganizeRequest,
    content_fetcher: ContentFetcherProtocol = Depends(get_content_fetcher),
    ai_organizer: AIOrganizerProtocol = Depends(get_ai_organizer),
    bookmark_builder: BookmarkBuilderProtocol = Depends(get_bookmark_builder),
) -> OrganizeResponse:
    """Analyze and propose organization for bookmarks."""
    try:
        service = OrganizationService(content_fetcher, ai_organizer, bookmark_builder)
        response = await service.organize(request.bookmarks, request.max_folders)
        if request.dry_run:
            logger.info(
                "Dry run complete: %d ops proposed",
                len(response.operations),
            )
        return response
    except Exception:
        logger.exception("Error organizing bookmarks")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        ) from None
