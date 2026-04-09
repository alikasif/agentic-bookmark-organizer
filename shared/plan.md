# Project Name: bookmarks_organizer

## Git Strategy
- **Branch**: `feat/ai-bookmark-organizer`
- **Base**: `main`
- Conventional commits on feature branch
- Never commit directly to main
- Open draft PR to main upon completion

---

## Overview
AI-Powered Microsoft Edge Bookmark Organizer. A browser extension + Python backend
system that reads a user's Edge bookmarks, fetches content from each URL, sends
them to Claude AI for intelligent categorization, and reorganizes the bookmarks
into a logical folder hierarchy.

---

## Architecture

### Backend (`backend/`)
- **Runtime**: Python 3.12
- **Framework**: FastAPI + uvicorn
- **Port**: `localhost:8765`
- **Key dependencies**: httpx, beautifulsoup4 (lxml), anthropic SDK, pydantic-settings
- **Responsibility**: All Claude API calls (key never exposed to browser), async HTTP
  content fetching, HTML parsing, bookmark operation generation

### Extension (`extension/`)
- **Type**: Browser Extension, Manifest V3
- **Language**: TypeScript, webpack bundled
- **Permissions**: `bookmarks`, `storage`, `http://localhost:8765/*`
- **Responsibility**: Read Chrome bookmarks tree, communicate with backend, apply
  operations back to bookmarks via chrome.bookmarks API, popup UI

---

## Module Layout

### Backend Modules
```
backend/src/bookmarks_organizer/
├── main.py              - FastAPI app factory + uvicorn entry point
├── config.py            - Settings via pydantic-settings (.env)
├── api/routes/
│   ├── health.py        - GET /health
│   ├── bookmarks.py     - POST /organize
│   └── content.py       - POST /content/fetch
├── services/
│   ├── protocols.py     - ContentFetcherProtocol, AIOrganizerProtocol
│   ├── content_fetcher.py - httpx async fetcher with semaphore rate limiting
│   ├── ai_organizer.py  - Claude API integration, batching, retry logic
│   └── bookmark_builder.py - OrganizeProposal → flat BookmarkOperation list
└── models/
    ├── requests.py      - BookmarkItem, OrganizeRequest, ContentFetchRequest
    └── responses.py     - OrganizeResponse, BookmarkOperation, FolderNode, etc.
```

### Extension Modules
```
extension/src/
├── background/
│   ├── service-worker.ts   - Message orchestration, main flow controller
│   ├── bookmark-reader.ts  - chrome.bookmarks.getTree() → flat BookmarkItem[]
│   ├── bookmark-writer.ts  - BookmarkOperation[] → chrome.bookmarks API calls
│   ├── backend-client.ts   - fetch() wrapper for backend API calls
│   └── progress-tracker.ts - chrome.storage.local job state persistence
├── popup/
│   ├── popup.html          - Extension popup shell
│   ├── popup.ts            - 7-state UI machine
│   └── popup.css           - Minimal clean styling
└── types/
    └── api.ts              - TypeScript interfaces matching backend models
```

---

## API Contracts

### GET /health
```
Response 200:
{ "status": "ok", "version": "1.0.0" }
```

### POST /organize
Request:
```json
{
  "bookmarks": [
    {
      "id": "123",
      "parent_id": "1",
      "title": "Python Docs",
      "url": "https://docs.python.org",
      "depth": 1
    }
  ],
  "dry_run": true,
  "max_folders": 20
}
```

Response 200:
```json
{
  "proposed_structure": {
    "name": "root",
    "children": [],
    "bookmark_ids": []
  },
  "operations": [
    {
      "op": "create_folder",
      "bookmark_id": null,
      "folder_path": ["Tech", "Python"],
      "new_title": null
    },
    {
      "op": "move",
      "bookmark_id": "123",
      "folder_path": ["Tech", "Python"],
      "new_title": "Python Official Docs"
    }
  ],
  "stats": {
    "total_bookmarks": 150,
    "folders_created": 12,
    "bookmarks_moved": 148
  },
  "warnings": ["Failed to fetch: https://example.com/broken"]
}
```

### POST /content/fetch
Request:
```json
{ "urls": ["https://example.com"] }
```

Response 200:
```json
{
  "results": [
    {
      "url": "https://example.com",
      "title": "Example Domain",
      "description": "A sample page",
      "success": true
    }
  ]
}
```

---

## Key Models

### Settings (config.py)
```python
class Settings(BaseSettings):
    anthropic_api_key: str
    backend_host: str = "127.0.0.1"
    backend_port: int = 8765
    fetch_concurrency: int = 10
    fetch_timeout_seconds: float = 5.0
    ai_batch_size: int = 50
    ai_model: str = "claude-3-5-haiku-20241022"
    cors_origins: list[str] = ["chrome-extension://*"]
    model_config = SettingsConfigDict(env_file=".env")
```

### Request Models
```python
class BookmarkItem(BaseModel):
    id: str
    parent_id: str | None
    title: str
    url: str | None
    depth: int

class OrganizeRequest(BaseModel):
    bookmarks: list[BookmarkItem]
    dry_run: bool = True
    max_folders: int = 20
```

### Response Models
```python
class BookmarkOperation(BaseModel):
    op: Literal["create_folder", "move", "rename"]
    bookmark_id: str | None
    folder_path: list[str]
    new_title: str | None

class FolderNode(BaseModel):
    name: str
    children: list["FolderNode"]
    bookmark_ids: list[str]

class OrganizeResponse(BaseModel):
    proposed_structure: FolderNode
    operations: list[BookmarkOperation]
    stats: dict[str, int]
    warnings: list[str]
```

### Protocols (Interface-First)
```python
class ContentFetcherProtocol(Protocol):
    async def fetch_batch(self, urls: list[str]) -> list[FetchedContent]: ...

class AIOrganizerProtocol(Protocol):
    async def organize(
        self, bookmarks: list[BookmarkWithContent]
    ) -> OrganizeProposal: ...
```

---

## Architectural Decisions

1. **Protocol-based design**: All services implement typed Protocols, enabling easy
   mocking in tests and future swappability.
2. **CORS with origin regex**: Backend uses `allow_origin_regex` for
   `chrome-extension://.*` since extension IDs change between installs.
3. **Dry-run by default**: All AI operations are dry-run first; user must confirm
   before mutations are applied.
4. **Content fetching**: Semaphore-limited concurrent httpx requests (default 10)
   prevent overwhelming target servers. Non-HTML and errors are handled gracefully.
5. **AI batching**: Bookmarks sent in batches of 50 to Claude to stay within context
   limits. Results are merged.
6. **JSON retry**: Malformed Claude responses trigger corrective prompts up to 3x
   before failing gracefully.
7. **API key security**: ANTHROPIC_API_KEY lives only in backend `.env`, never
   accessible to the browser extension.
8. **TypeScript strict mode**: Extension code uses strict TypeScript to catch errors
   at compile time.

---

## Architectural Decision Log

### 2026-04-06 — Architecture Review: DI and Separation of Concerns

**Context:** First architectural review of the backend. The module boundary direction
(api -> services -> models) is correct and there are no circular imports. However,
the route layer directly instantiates concrete service implementations, bypassing the
protocol abstractions defined in `protocols.py`.

**Decisions:**
1. All service dependencies in route handlers MUST be injected via FastAPI `Depends()`
   functions typed to the corresponding Protocol. Direct instantiation of services in
   routes is not permitted.
2. Orchestration logic (multi-step workflows like fetch->enrich->organize->build) MUST
   live in the service layer, not in route handlers. Route handlers should perform only
   request parsing, delegation, and response mapping.
3. Service constructors MUST accept only the specific configuration values they need,
   not the full `Settings` object. Wiring happens in the DI/dependency layer.
4. Every service class MUST have a corresponding Protocol in `services/protocols.py`.
   This includes `BookmarkBuilder`.

---

## GitHub Details
- **Repo**: `d:/GitHub/bookmarks-organizer`
- **Branch**: `feat/ai-bookmark-organizer`
- **Git user**: kasif
