"""Tests for BookmarkBuilder service."""

import os

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture
def builder():
    """Return a BookmarkBuilder instance."""
    from bookmarks_organizer.services.bookmark_builder import BookmarkBuilder

    return BookmarkBuilder()


def test_build_response_orders_operations(builder) -> None:
    """Folder create ops come before move ops, parents before children."""
    from bookmarks_organizer.models.requests import BookmarkItem
    from bookmarks_organizer.models.responses import (
        BookmarkOperation,
        FolderNode,
        OrganizeProposal,
    )

    proposal = OrganizeProposal(
        proposed_structure=FolderNode(name="root"),
        operations=[
            BookmarkOperation(
                op="move",
                bookmark_id="1",
                folder_path=["Tech", "Python"],
                new_title=None,
            ),
            BookmarkOperation(
                op="create_folder",
                bookmark_id=None,
                folder_path=["Tech", "Python"],
                new_title=None,
            ),
            BookmarkOperation(
                op="create_folder",
                bookmark_id=None,
                folder_path=["Tech"],
                new_title=None,
            ),
        ],
        warnings=[],
    )
    bookmarks = [
        BookmarkItem(id="1", title="Python", url="https://python.org", depth=1)
    ]
    response = builder.build_response(proposal, bookmarks)
    ops = response.operations
    assert ops[0].op == "create_folder"
    assert ops[1].op == "create_folder"
    assert len(ops[0].folder_path) <= len(ops[1].folder_path)
    assert ops[2].op == "move"


def test_build_response_stats(builder) -> None:
    """Stats are correctly calculated."""
    from bookmarks_organizer.models.requests import BookmarkItem
    from bookmarks_organizer.models.responses import (
        BookmarkOperation,
        FolderNode,
        OrganizeProposal,
    )

    proposal = OrganizeProposal(
        proposed_structure=FolderNode(name="root"),
        operations=[
            BookmarkOperation(
                op="create_folder",
                bookmark_id=None,
                folder_path=["Tech"],
                new_title=None,
            ),
            BookmarkOperation(
                op="move",
                bookmark_id="1",
                folder_path=["Tech"],
                new_title=None,
            ),
        ],
        warnings=[],
    )
    bookmarks = [
        BookmarkItem(id="1", title="Test", url="https://test.com", depth=1),
        BookmarkItem(id="2", title="Test2", url="https://test2.com", depth=1),
    ]
    response = builder.build_response(proposal, bookmarks)
    assert response.stats["total_bookmarks"] == 2
    assert response.stats["folders_created"] == 1
    assert response.stats["bookmarks_moved"] == 1


def test_enrich_bookmarks(builder) -> None:
    """Enriches bookmarks with fetched content."""
    from bookmarks_organizer.models.requests import BookmarkItem
    from bookmarks_organizer.models.responses import FetchedContent

    bm = BookmarkItem(id="1", title="Python", url="https://python.org", depth=1)
    fetched = [
        FetchedContent(
            url="https://python.org",
            title="Python.org",
            description="The Python language",
            success=True,
        )
    ]
    enriched = builder.enrich_bookmarks([bm], fetched)
    assert enriched[0].fetched_title == "Python.org"
    assert enriched[0].description == "The Python language"


def test_enrich_bookmarks_missing_content(builder) -> None:
    """Handles bookmarks with no matching fetched content."""
    from bookmarks_organizer.models.requests import BookmarkItem

    bm = BookmarkItem(id="1", title="Test", url="https://test.com", depth=1)
    enriched = builder.enrich_bookmarks([bm], [])
    assert enriched[0].fetched_title == ""
    assert enriched[0].description == ""
