"""Response models for the bookmark organizer API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class FolderNode(BaseModel):
    """A node in the proposed folder tree."""

    name: str
    children: list[FolderNode] = []
    bookmark_ids: list[str] = []


FolderNode.model_rebuild()


class BookmarkOperation(BaseModel):
    """A single bookmark operation to perform."""

    op: Literal["create_folder", "move", "rename"]
    bookmark_id: str | None = None
    folder_path: list[str]
    new_title: str | None = None


class OrganizeResponse(BaseModel):
    """Response from the organize endpoint."""

    proposed_structure: FolderNode
    operations: list[BookmarkOperation]
    stats: dict[str, int]
    warnings: list[str]


class FetchedContent(BaseModel):
    """Content fetched from a URL."""

    url: str
    title: str = ""
    description: str = ""
    body_text: str = ""
    success: bool
    error: str = ""


class ContentFetchResponse(BaseModel):
    """Response from the content fetch endpoint."""

    results: list[FetchedContent]


class BookmarkWithContent(BaseModel):
    """A bookmark enriched with fetched content."""

    id: str
    parent_id: str | None = None
    title: str
    url: str | None = None
    depth: int
    fetched_title: str = ""
    description: str = ""
    body_text: str = ""


class OrganizeProposal(BaseModel):
    """Proposal returned by the AI organizer."""

    proposed_structure: FolderNode
    operations: list[BookmarkOperation]
    warnings: list[str] = []
