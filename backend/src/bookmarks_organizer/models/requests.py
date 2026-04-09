"""Request models for the bookmark organizer API."""

from pydantic import BaseModel, Field


class BookmarkItem(BaseModel):
    """A single bookmark item."""

    id: str
    parent_id: str | None = None
    title: str
    url: str | None = None
    depth: int


class OrganizeRequest(BaseModel):
    """Request to organize bookmarks."""

    bookmarks: list[BookmarkItem] = Field(max_length=5000)
    dry_run: bool = True
    max_folders: int = 20


class ContentFetchRequest(BaseModel):
    """Request to fetch content for URLs."""

    urls: list[str] = Field(max_length=500)
