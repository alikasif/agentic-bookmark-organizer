"""Tests for AIOrganizer service."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")


@pytest.fixture
def organizer():
    """Return an AIOrganizer instance."""
    from bookmarks_organizer.services.ai_organizer import AIOrganizer

    return AIOrganizer(
        api_key="test-key",
        model="openai/gpt-4o",
        base_url="https://openrouter.ai/api/v1",
        batch_size=50,
    )


def make_valid_response_json() -> str:
    """Return a valid AI response JSON string."""
    return json.dumps(
        {
            "proposed_structure": {
                "name": "root",
                "children": [{"name": "Tech", "children": [], "bookmark_ids": ["1"]}],
                "bookmark_ids": [],
            },
            "operations": [
                {
                    "op": "create_folder",
                    "bookmark_id": None,
                    "folder_path": ["Tech"],
                    "new_title": None,
                },
                {
                    "op": "move",
                    "bookmark_id": "1",
                    "folder_path": ["Tech"],
                    "new_title": None,
                },
            ],
            "warnings": [],
        }
    )


@pytest.mark.anyio
async def test_organize_valid_response(organizer) -> None:
    """Returns valid proposal when AI returns correct JSON."""
    from bookmarks_organizer.models.responses import BookmarkWithContent

    bookmarks = [
        BookmarkWithContent(id="1", title="Python", url="https://python.org", depth=1)
    ]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = make_valid_response_json()

    with patch.object(
        organizer._client.chat.completions,
        "create",
        new=AsyncMock(return_value=mock_response),
    ):
        proposal = await organizer.organize(bookmarks, max_folders=20)

    assert len(proposal.operations) == 2
    assert proposal.operations[0].op == "create_folder"
    assert proposal.operations[1].op == "move"


@pytest.mark.anyio
async def test_organize_empty_bookmarks(organizer) -> None:
    """Returns empty proposal for empty bookmark list."""
    proposal = await organizer.organize([])
    assert proposal.operations == []
    assert proposal.warnings == []


@pytest.mark.anyio
async def test_organize_retries_on_bad_json(organizer) -> None:
    """Retries up to 3 times on malformed JSON, returns empty on all failures."""
    from bookmarks_organizer.models.responses import BookmarkWithContent

    bookmarks = [
        BookmarkWithContent(id="1", title="Test", url="https://test.com", depth=1)
    ]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "not valid json {{{"

    with patch.object(
        organizer._client.chat.completions,
        "create",
        new=AsyncMock(return_value=mock_response),
    ) as mock_create:
        proposal = await organizer.organize(bookmarks, max_folders=20)

    assert mock_create.call_count == 3
    assert len(proposal.warnings) > 0
    assert proposal.operations == []


@pytest.mark.anyio
async def test_organize_batches_large_input(organizer) -> None:
    """Splits bookmarks into batches when exceeding batch size."""
    from bookmarks_organizer.models.responses import BookmarkWithContent

    # Set a tiny batch size for testing
    organizer._batch_size = 2
    bookmarks = [
        BookmarkWithContent(
            id=str(i), title=f"BM{i}", url=f"https://bm{i}.com", depth=1
        )
        for i in range(5)
    ]
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(
        {
            "proposed_structure": {"name": "root", "children": [], "bookmark_ids": []},
            "operations": [],
            "warnings": [],
        }
    )
    with patch.object(
        organizer._client.chat.completions,
        "create",
        new=AsyncMock(return_value=mock_response),
    ) as mock_create:
        proposal = await organizer.organize(bookmarks, max_folders=20)

    # 5 bookmarks / 2 batch size = 3 batches
    assert mock_create.call_count == 3
    assert proposal is not None
