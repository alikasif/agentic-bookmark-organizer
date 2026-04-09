"""Builds bookmark operation lists from organize proposals."""

import logging

from bookmarks_organizer.models.requests import BookmarkItem
from bookmarks_organizer.models.responses import (
    BookmarkOperation,
    BookmarkWithContent,
    FetchedContent,
    OrganizeProposal,
    OrganizeResponse,
)

logger = logging.getLogger(__name__)


class BookmarkBuilder:
    """Converts organize proposals into ordered operation lists."""

    def build_response(
        self,
        proposal: OrganizeProposal,
        original_bookmarks: list[BookmarkItem],
    ) -> OrganizeResponse:
        """Build an OrganizeResponse from a proposal."""
        create_ops = [op for op in proposal.operations if op.op == "create_folder"]
        other_ops = [op for op in proposal.operations if op.op != "create_folder"]

        sorted_creates = self._sort_folder_creates(create_ops)
        ordered_ops = sorted_creates + other_ops

        folders_created = len(create_ops)
        bookmarks_moved = sum(1 for op in other_ops if op.op == "move")

        return OrganizeResponse(
            proposed_structure=proposal.proposed_structure,
            operations=ordered_ops,
            stats={
                "total_bookmarks": len(original_bookmarks),
                "folders_created": folders_created,
                "bookmarks_moved": bookmarks_moved,
            },
            warnings=proposal.warnings,
        )

    def enrich_bookmarks(
        self,
        bookmarks: list[BookmarkItem],
        fetched: list[FetchedContent],
    ) -> list[BookmarkWithContent]:
        """Merge bookmark items with fetched content."""
        fetch_map = {f.url: f for f in fetched if f.url}
        enriched = []
        for bm in bookmarks:
            content = fetch_map.get(bm.url or "", None)
            enriched.append(
                BookmarkWithContent(
                    id=bm.id,
                    parent_id=bm.parent_id,
                    title=bm.title,
                    url=bm.url,
                    depth=bm.depth,
                    fetched_title=content.title if content else "",
                    description=content.description if content else "",
                    body_text=content.body_text if content else "",
                )
            )
        return enriched

    def _sort_folder_creates(
        self, ops: list[BookmarkOperation]
    ) -> list[BookmarkOperation]:
        """Sort create_folder ops so parents are created before children."""
        return sorted(ops, key=lambda op: len(op.folder_path))
