# Architecture

## Overview

The AI Bookmark Organizer is a two-component system:

1. **Browser Extension** (TypeScript, Manifest V3) — runs in the browser, reads
   bookmarks, presents the popup UI, and applies changes via `chrome.bookmarks` API.
2. **Python Backend** (FastAPI) — handles all AI API calls and content fetching,
   runs locally at `localhost:8765`.

The API key lives exclusively in `backend/.env`. It is never transmitted to or
accessible by the browser extension.

---

## Component Diagram

```
+------------------------------------------+
|           Microsoft Edge                 |
|                                          |
|  +------------------------------------+  |
|  | Popup (popup.ts — 7-state machine) |  |
|  | idle | fetching | analyzing        |  |
|  | preview | applying | done | error  |  |
|  +------------------+-----------------+  |
|                     | chrome.runtime      |
|                     | sendMessage()       |
|  +------------------v-----------------+  |
|  | Service Worker (service-worker.ts) |  |
|  |                                    |  |
|  |  BookmarkReader   BookmarkWriter   |  |
|  |  BackendClient    ProgressTracker  |  |
|  +------------------+-----------------+  |
+---------------------|--------------------+
                       | HTTP / JSON
              (localhost:8765)
+---------------------------+---------------------------+
|       Python Backend      |                           |
|                           |                           |
|  +---------------------+  |                           |
|  | FastAPI Routes      |  |                           |
|  | GET  /health        |  |                           |
|  | POST /organize      |  |                           |
|  | POST /content/fetch |  |                           |
|  +--------+------------+  |                           |
|           | FastAPI Depends()                         |
|  +--------v------------+  |                           |
|  | OrganizationService |  |                           |
|  | (orchestration)     |  |                           |
|  +--+--------+------+--+  |                           |
|     |        |      |     |                           |
|  +--v--+  +--v--+  ++--+  |   +------------------+   |
|  |Cont-|  | AI  |  |Bkm|  |   | Claude API       |   |
|  |ent  |  |Org- |  |mk |  +-->| (Anthropic)      |   |
|  |Fetch|  |aniz-|  |Bld|  |   | claude-3-5-haiku |   |
|  |er   |  |er   |  |er |  |   +------------------+   |
|  +--+--+  +-----+  +---+  |                           |
|     |                     |   +------------------+   |
|     +--httpx------------->+-->| External URLs    |   |
|     |  AsyncClient        |   | (target websites)|   |
|     |  Semaphore(10)      |   +------------------+   |
+-----|---------------------+                           |
      +---------------------------------------------------+
```

---

## Data Flow

The full lifecycle from user click to applied changes:

```
1.  User clicks "Organize Bookmarks" in the popup
2.  popup.ts sends  { type: 'START_ORGANIZE' }  to service worker
3.  Service worker: BookmarkReader.readAll()
    - chrome.bookmarks.getTree() -> flatten to BookmarkItem[]
    - Synthetic root nodes are skipped
4.  Service worker: BackendClient.organize(bookmarks, dryRun=true)
    - POST /organize  { bookmarks, dry_run: true, max_folders: 20 }
5.  Backend: OrganizationService.organize()
    a. ContentFetcher.fetch_batch(urls)
       - httpx.AsyncClient with asyncio.Semaphore(10)
       - BeautifulSoup4 (lxml): extracts title, meta description, body[:500]
       - Non-HTML, timeouts, and errors return FetchedContent(success=False)
       - Only http:// and https:// URLs are fetched (SSRF guard)
    b. BookmarkBuilder.enrich_bookmarks(bookmarks, fetched)
       - Merges fetched content into BookmarkWithContent objects
    c. AIOrganizer.organize(enriched, max_folders)
       - Splits into chunks of ai_batch_size (default 50)
       - Each chunk: POST to Claude claude-3-5-haiku-20241022
       - Validates JSON response with Pydantic; retries up to 3x on failure
       - Multi-chunk results are merged into a single OrganizeProposal
    d. BookmarkBuilder.build_response(proposal, original_bookmarks)
       - Sorts create_folder ops by path depth (parents before children)
       - Counts stats: total_bookmarks, folders_created, bookmarks_moved
6.  Backend returns OrganizeResponse to extension
7.  Service worker sends  { type: 'PREVIEW', payload: response }  to popup
8.  popup.ts renders proposed_structure as a collapsible folder tree
9.  User clicks Apply  ->  popup sends  { type: 'CONFIRM' }
10. Service worker: BookmarkWriter.applyOperations(operations)
    - Processes create_folder ops first (folder cache avoids duplicate creates)
    - chrome.bookmarks.create() for each new folder
    - chrome.bookmarks.move() for each move op
    - chrome.bookmarks.update() for each rename op
11. Service worker sends  { type: 'DONE', payload: { count } }  to popup
12. Popup shows Done state with operation count
```

---

## Backend Modules

### `config.py`

Loads application settings from the `.env` file using `pydantic-settings`.

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
```

`get_settings()` is decorated with `@lru_cache` — it returns the same `Settings`
instance on every call, reading `.env` only once at startup.

---

### `models/requests.py`

Request models validated by FastAPI on every incoming request.

| Model | Fields | Notes |
|-------|--------|-------|
| `BookmarkItem` | `id`, `parent_id`, `title`, `url`, `depth` | `url` and `parent_id` are optional (folders have no URL) |
| `OrganizeRequest` | `bookmarks` (max 5000), `dry_run=True`, `max_folders=20` | `dry_run=True` is the safe default |
| `ContentFetchRequest` | `urls` (max 500) | Bounded list prevents resource exhaustion |

---

### `models/responses.py`

Response models serialized by FastAPI.

| Model | Purpose |
|-------|---------|
| `FolderNode` | Tree node: `name`, `children: list[FolderNode]`, `bookmark_ids: list[str]` |
| `BookmarkOperation` | One change: `op` (`create_folder` / `move` / `rename`), `bookmark_id`, `folder_path`, `new_title` |
| `OrganizeResponse` | Full response: `proposed_structure`, `operations`, `stats`, `warnings` |
| `FetchedContent` | Per-URL fetch result: `url`, `title`, `description`, `body_text`, `success`, `error` |
| `ContentFetchResponse` | Wraps `list[FetchedContent]` |
| `BookmarkWithContent` | Bookmark merged with fetched content for AI input |
| `OrganizeProposal` | Internal AI output before stats are added |

---

### `services/protocols.py`

Typed `Protocol` interfaces that decouple route handlers from concrete services.

```python
class ContentFetcherProtocol(Protocol):
    async def fetch_batch(self, urls: list[str]) -> list[FetchedContent]: ...

class AIOrganizerProtocol(Protocol):
    async def organize(
        self, bookmarks: list[BookmarkWithContent], max_folders: int = 20
    ) -> OrganizeProposal: ...

class BookmarkBuilderProtocol(Protocol):
    def build_response(
        self, proposal: OrganizeProposal, original_bookmarks: list[BookmarkItem]
    ) -> OrganizeResponse: ...

    def enrich_bookmarks(
        self, bookmarks: list[BookmarkItem], fetched: list[FetchedContent]
    ) -> list[BookmarkWithContent]: ...
```

---

### `services/content_fetcher.py` — `ContentFetcher`

Fetches and parses HTML from a list of URLs concurrently.

- Uses `httpx.AsyncClient` with `follow_redirects=True`
- Concurrency is controlled by `asyncio.Semaphore(concurrency)` (default 10)
- Only `http://` and `https://` URLs are fetched; others return `success=False`
- Non-HTML `Content-Type` responses return `success=False` without parsing
- BeautifulSoup4 (lxml parser) extracts:
  - `<title>` tag, fallback to `<h1>`
  - `<meta name="description">` or `<meta property="og:description">`
  - First 500 characters of visible body text (after stripping `script`, `style`,
    `nav`, `footer`, `header` tags)
- All network errors (timeout, connection error, HTTP error) are caught and return
  `success=False` — they never propagate to the caller

---

### `services/ai_organizer.py` — `AIOrganizer`

Organizes bookmark batches using the Claude API.

- Uses `anthropic.AsyncAnthropic`
- Splits input into chunks of `batch_size` (default 50)
- Each chunk is sent as a single Claude request with a system prompt instructing
  JSON-only output matching the `OrganizeProposal` schema
- `max_folders` is substituted into the prompt via the `__MAX_FOLDERS__` placeholder
- Response is parsed with `OrganizeProposal.model_validate()`; on failure a
  corrective prompt is appended and the request retried up to 3 times
- Multi-batch results are merged: operations and warnings are concatenated; folder
  trees are joined under the root node
- On total failure returns an empty `OrganizeProposal` with a warning

---

### `services/bookmark_builder.py` — `BookmarkBuilder`

Converts an `OrganizeProposal` into a fully-ordered `OrganizeResponse`.

- `enrich_bookmarks()`: merges `BookmarkItem` list with fetched content by URL
- `build_response()`: separates `create_folder` from `move`/`rename` operations,
  sorts `create_folder` ops by `folder_path` length (shortest path first, so
  parents are created before children), then appends move/rename ops
- Computes stats: `total_bookmarks`, `folders_created`, `bookmarks_moved`

---

### `services/organization_service.py` — `OrganizationService`

Orchestrates the full workflow, keeping route handlers free of business logic.

```
organize(bookmarks, max_folders)
  -> ContentFetcher.fetch_batch(urls)
  -> BookmarkBuilder.enrich_bookmarks(bookmarks, fetched)
  -> AIOrganizer.organize(enriched, max_folders)
  -> BookmarkBuilder.build_response(proposal, bookmarks)
```

---

### `api/dependencies.py`

FastAPI `Depends()` factory functions. Each returns a concrete service typed to
its protocol. `get_settings()` is called here (cached via `lru_cache`).

```python
def get_content_fetcher() -> ContentFetcherProtocol: ...
def get_ai_organizer()    -> AIOrganizerProtocol: ...
def get_bookmark_builder()-> BookmarkBuilderProtocol: ...
```

---

### `api/routes/health.py`

```
GET /health  ->  { "status": "ok", "version": "1.0.0" }
```

---

### `api/routes/bookmarks.py`

```
POST /organize
```

Injects the three service dependencies via `Depends()`, delegates to
`OrganizationService.organize()`, logs dry-run vs. live mode, and wraps all
exceptions in a generic `500 Internal Server Error` to avoid leaking stack traces.

---

### `api/routes/content.py`

```
POST /content/fetch
```

Injects `ContentFetcher` via `Depends()`, calls `fetch_batch()`, and returns
`ContentFetchResponse`. Exceptions return a generic `500`.

---

### `main.py`

- `create_app()` builds the `FastAPI` instance, adds `CORSMiddleware` with
  `allow_origin_regex=r"chrome-extension://.*"`, and includes all routers.
- `export_openapi()` walks up the directory tree to find the repo root and writes
  the OpenAPI schema to `shared/api/openapi.json`.
- `if __name__ == "__main__"` block calls `export_openapi()` then starts uvicorn.

---

## Extension Components

### `types/api.ts`

TypeScript interfaces that mirror the backend Pydantic models exactly:
`BookmarkItem`, `OrganizeRequest`, `OrganizeResponse`, `BookmarkOperation`,
`FolderNode`, `HealthResponse`, `FetchedContent`, `ContentFetchResponse`.

Also defines the `MessageType` union (`START_ORGANIZE | CANCEL | CONFIRM | PREVIEW
| PROGRESS | DONE | ERROR`) and the `ExtensionMessage` envelope type.

---

### `background/service-worker.ts`

The persistent background context. Registers a `chrome.runtime.onMessage` listener
that handles three inbound message types:

| Message | Handler |
|---------|---------|
| `START_ORGANIZE` | Reads bookmarks, calls backend with `dry_run=true`, emits `PREVIEW` |
| `CONFIRM` | Applies `pendingOperations` via `BookmarkWriter`, emits `DONE` |
| `CANCEL` | Sets tracker state to idle |

Errors in either handler are caught and emitted as `ERROR` messages to the popup.

---

### `background/bookmark-reader.ts` — `BookmarkReader`

- `readAll()`: calls `chrome.bookmarks.getTree()` and flattens the tree to a
  `BookmarkItem[]`
- Skips the synthetic root nodes that Chrome inserts at depth 0
- Folder nodes (no `url`) are included so the AI can see existing structure

---

### `background/bookmark-writer.ts` — `BookmarkWriter`

- `applyOperations(operations)`: processes `create_folder` ops first, then
  `move` and `rename` ops
- `createFolder(path)`: walks the path segments, creating only missing folders;
  caches created folder IDs by path string to avoid duplicate creates within a
  single apply session
- `moveBookmark`: resolves target folder ID, calls `chrome.bookmarks.move()`,
  then optionally `chrome.bookmarks.update()` if a `new_title` is provided
- `renameBookmark`: calls `chrome.bookmarks.update()` with the new title

---

### `background/backend-client.ts` — `BackendClient`

Thin `fetch()` wrapper. Base URL defaults to `http://localhost:8765`.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `checkHealth()` | `GET /health` | Verify backend is running |
| `organize(bookmarks, dryRun, maxFolders)` | `POST /organize` | Request AI organization |
| `fetchContent(urls)` | `POST /content/fetch` | Fetch URL metadata |

All methods throw `Error` on non-OK HTTP responses with status code included in
the message.

---

### `background/progress-tracker.ts` — `ProgressTracker`

Persists `JobState` to `chrome.storage.local` under the key `job_state`.

```typescript
interface JobState {
  status: 'idle' | 'fetching' | 'analyzing' | 'preview' | 'applying' | 'done' | 'error';
  progress: number;
  total: number;
  errors: string[];
  message?: string;
}
```

Methods: `getState()`, `setState(partial)` (merges with current), `reset()`.

---

### `popup/popup.ts`

Implements a 7-state UI machine. Each state maps to a `<div id="state-{name}">` in
`popup.html` that is shown/hidden via the `hidden` CSS class.

| State | Shown when |
|-------|------------|
| `idle` | Initial state; shows Organize button and backend status chip |
| `fetching` | Reading bookmarks from browser |
| `analyzing` | Backend is processing (fetching URLs + calling Claude) |
| `preview` | `PREVIEW` message received; renders folder tree and stats |
| `applying` | `CONFIRM` sent; `BookmarkWriter` is running |
| `done` | `DONE` received; shows operation count |
| `error` | Any error; shows message and Retry button |

On `DOMContentLoaded`: calls `checkBackendStatus()` (polls `GET /health`),
enables or disables the Organize button based on result, and registers button
event listeners and the `chrome.runtime.onMessage` listener.

---

## API Contract Reference

### `GET /health`

```
Response 200:
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

### `POST /organize`

Request body:

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

Constraints: `bookmarks` max length 5000; `dry_run` defaults to `true`.

Response 200:

```json
{
  "proposed_structure": {
    "name": "root",
    "children": [
      {
        "name": "Tech",
        "children": [
          { "name": "Python", "children": [], "bookmark_ids": ["123"] }
        ],
        "bookmark_ids": []
      }
    ],
    "bookmark_ids": []
  },
  "operations": [
    { "op": "create_folder", "bookmark_id": null,
      "folder_path": ["Tech"], "new_title": null },
    { "op": "create_folder", "bookmark_id": null,
      "folder_path": ["Tech", "Python"], "new_title": null },
    { "op": "move", "bookmark_id": "123",
      "folder_path": ["Tech", "Python"], "new_title": "Python Official Docs" }
  ],
  "stats": {
    "total_bookmarks": 1,
    "folders_created": 2,
    "bookmarks_moved": 1
  },
  "warnings": []
}
```

`create_folder` ops are always ordered before `move`/`rename` ops, and parent
folders always appear before their children. `warnings` contains non-fatal
messages such as URLs that failed to fetch or AI retry exhaustion.

Error responses: `422 Unprocessable Entity` for invalid request bodies;
`500 Internal Server Error` for backend failures (detail is generic to avoid
leaking internals).

---

### `POST /content/fetch`

Request body:

```json
{ "urls": ["https://example.com", "https://docs.python.org"] }
```

Constraints: `urls` max length 500.

Response 200:

```json
{
  "results": [
    {
      "url": "https://example.com",
      "title": "Example Domain",
      "description": "This domain is for use in illustrative examples.",
      "body_text": "Example Domain This domain is for use...",
      "success": true,
      "error": ""
    },
    {
      "url": "https://broken.example/404",
      "title": "",
      "description": "",
      "body_text": "",
      "success": false,
      "error": ""
    }
  ]
}
```

Every URL in the request appears in `results` regardless of success. Failed fetches
have `success: false` and empty content fields.

---

## Key Architectural Decisions

### 1. Protocol-Based Dependency Injection

All backend services implement typed `Protocol` interfaces defined in
`services/protocols.py`. Route handlers depend only on the protocol types, injected
via FastAPI `Depends()` factories in `api/dependencies.py`. This makes the
dependency direction explicit and allows test doubles to be substituted without
modifying production code.

### 2. OrganizationService Orchestration Layer

Multi-step workflows (fetch → enrich → organize → build) live in
`OrganizationService`, not in route handlers. Route handlers parse the request,
call the service, and map the result to a response. This keeps the API layer thin
and the business logic testable in isolation.

### 3. Dry-Run Default

`OrganizeRequest.dry_run` defaults to `True`. The backend always computes and
returns the full operations list regardless of `dry_run` value — the flag signals
intent to the caller. The extension's service worker holds operations in
`pendingOperations` and only applies them after the user clicks Apply
(`CONFIRM` message). This prevents irreversible bookmark mutations without
explicit confirmation.

### 4. Operations-Based Response Format

Rather than describing a desired end-state (e.g., a new tree structure), the API
returns an ordered list of discrete `BookmarkOperation` objects. The client applies
them sequentially using the native bookmarks API. This makes the intent auditable,
previews human-readable, and application atomic per-operation.

### 5. CORS Origin Regex

Chrome extension IDs are assigned at install time and differ across machines and
installs. Using `allow_origin_regex=r"chrome-extension://.*"` accepts any extension
origin without requiring the backend to know the specific ID.

### 6. Semaphore-Limited Content Fetching

`ContentFetcher` caps concurrent outbound HTTP requests at `fetch_concurrency`
(default 10) using `asyncio.Semaphore`. This balances throughput against courtesy
to target servers. All errors are caught per-URL so one failing URL cannot block
others or surface to the route layer.

### 7. AI Batching and JSON Retry

Bookmarks are processed in chunks of `ai_batch_size` (default 50) to stay within
Claude's context window. Multi-batch results are merged before returning to the
caller. Malformed JSON responses from Claude trigger a corrective follow-up prompt
up to 3 times before returning an empty proposal with a warning.

### 8. Haiku Model for Cost Efficiency

`claude-3-5-haiku-20241022` provides fast, low-cost categorization suitable for
batch bookmark analysis. The model is configurable via `AI_MODEL` in `.env` without
code changes.

### 9. Topological Folder Creation

`BookmarkBuilder._sort_folder_creates()` orders `create_folder` operations by
`folder_path` length (ascending). This guarantees that `["Tech"]` is created before
`["Tech", "Python"]`, preventing `chrome.bookmarks.create()` failures caused by
missing parent folders. `BookmarkWriter` applies the same separation client-side,
with a path-keyed cache to avoid duplicate folder creation.

### 10. API Key Security

`ANTHROPIC_API_KEY` exists only in `backend/.env`. It is loaded by `pydantic-settings`
at startup and passed directly to `anthropic.AsyncAnthropic`. It is never serialized
into any response, logged, or included in the OpenAPI schema.
