# AI-Powered Edge Bookmark Organizer

An intelligent browser extension + Python backend that uses AI to analyze
and reorganize your Microsoft Edge bookmarks into a logical folder structure.

## What It Does

- Reads all bookmarks from your browser
- Fetches content metadata from each URL (title, meta description, body text)
- Sends bookmarks to an AI model (via OpenRouter) for intelligent
  categorization and folder assignment
- Shows a dry-run preview of the proposed folder hierarchy before making any changes
- Applies the reorganization via the browser bookmarks API only after you confirm

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 18+ and npm
- Microsoft Edge (or any Chromium-based browser supporting Manifest V3 extensions)
- An [OpenRouter API key](https://openrouter.ai/)

## Backend Setup

```bash
cd backend
uv sync
cp .env.example .env
```

Edit `.env` and set your API key:

```
OPENROUTER_API_KEY=your_actual_api_key_here
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=openai/gpt-4o
```

Start the backend server:

```bash
cd backend && uv run python -m bookmarks_organizer.main
```

The backend runs at `http://localhost:8765`. It also exports the OpenAPI schema to
`shared/api/openapi.json` on startup.

### Backend Configuration

All settings are read from `backend/.env`. Defaults are shown below.

| Setting                 | Default                     | Description                         |
|-------------------------|-----------------------------|-------------------------------------|
| `OPENROUTER_API_KEY`    | (required)                  | Your OpenRouter API key             |
| `AI_BASE_URL`           | `https://openrouter.ai/api/v1` | AI API endpoint URL              |
| `BACKEND_HOST`          | `127.0.0.1`                 | Host to bind the server             |
| `BACKEND_PORT`          | `8765`                      | Port to listen on                   |
| `FETCH_CONCURRENCY`     | `10`                        | Max concurrent URL fetch requests   |
| `FETCH_TIMEOUT_SECONDS` | `5.0`                       | Per-request timeout in seconds      |
| `AI_BATCH_SIZE`         | `50`                        | Bookmarks per Claude API call       |
| `AI_MODEL`              | `claude-3-5-haiku-20241022` | Claude model to use                 |

## Extension Setup

```bash
cd extension
npm install
npm run build
```

### Loading in Microsoft Edge

1. Open `edge://extensions/`
2. Enable **Developer mode** (toggle in the bottom-left corner)
3. Click **Load unpacked**
4. Select the `extension/` folder (the folder containing `manifest.json`, **not**
   `extension/dist/`)
5. The **AI Bookmark Organizer** icon appears in the toolbar

> Chrome users: the same steps apply at `chrome://extensions/`.

## Usage

1. Start the backend server (see above).
2. Click the **AI Bookmark Organizer** extension icon in the toolbar.
3. The popup shows **Backend: Online** when the server is reachable.
4. Click **Organize Bookmarks**.
5. Wait while the extension reads your bookmarks and the AI analyzes them.
6. Review the proposed folder structure in the preview panel — it shows folder
   names and how many bookmarks each folder will receive.
7. Click **Apply** to reorganize, or **Cancel** to discard.

Dry-run is the default: no bookmarks are moved until you explicitly click Apply.

## Architecture Overview

```
+---------------------------+     HTTP / JSON     +---------------------------+
|  Microsoft Edge           |                     |  Python Backend           |
|                           |  POST /organize     |  (localhost:8765)         |
|  Service Worker           +-------------------> |                           |
|  - BookmarkReader         |                     |  FastAPI routes           |
|  - BackendClient          | <------------------ |  - GET  /health           |
|  - BookmarkWriter         |  OrganizeResponse   |  - POST /organize         |
|  - ProgressTracker        |                     |  - POST /content/fetch    |
|                           |                     |           |               |
|  Popup UI (7 states)      |                     |  Services                 |
|  - idle / fetching        |                     |  - ContentFetcher         |
|  - analyzing / preview    |                     |  - AIOrganizer            |
|  - applying / done        |                     |  - BookmarkBuilder        |
|  - error                  |                     |  - OrganizationService    |
+---------------------------+                     +---------------------------+
                                                           |           |
                                                  +--------+    +------+------+
                                                  | Claude |    | External    |
                                                  | API    |    | URLs (httpx)|
                                                  +--------+    +-------------+
```

The browser extension communicates only with the local backend. The backend holds
the Anthropic API key and makes all Claude API calls — the key is never sent to or
accessible by the browser.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Dry-run default | Prevents irreversible bookmark mutations without user confirmation |
| Operations-based response | Provides a precise, ordered list of changes the client applies atomically |
| `claude-3-5-haiku-20241022` | Balances cost and speed for batch categorization tasks |
| Semaphore-limited content fetching | Caps concurrent outbound requests at 10 to avoid overwhelming target servers |
| Protocol-based service injection | All services implement typed Protocols; FastAPI `Depends()` wires concretions, enabling easy test mocking |
| CORS origin regex | Extension IDs change between installs; `allow_origin_regex` avoids hardcoding them |
| AI batch size of 50 | Stays well within Claude's context window while keeping round-trips manageable |
| JSON retry (3 attempts) | Corrective prompts recover from occasional malformed Claude responses gracefully |

## Development

### Run the backend tests

```bash
cd backend
uv run pytest tests/ -v
```

### Build the extension in watch mode

```bash
cd extension
npm run dev
```

### Project structure

```
bookmarks-organizer/
├── backend/          Python 3.12 / FastAPI backend
├── extension/        TypeScript Manifest V3 browser extension
├── shared/           API contracts, project coordination files
└── docs/             Architecture documentation
```

See [docs/architecture.md](docs/architecture.md) for a full technical reference.
