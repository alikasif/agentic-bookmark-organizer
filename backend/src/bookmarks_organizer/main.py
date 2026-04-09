"""FastAPI application factory and entry point."""

import json
import logging
import pathlib

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bookmarks_organizer.api.routes import bookmarks, content, health
from bookmarks_organizer.config import get_settings

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Bookmark Organizer API",
        description="AI-powered bookmark organization backend",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"chrome-extension://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(bookmarks.router)
    app.include_router(content.router)

    return app


app = create_app()


def _find_repo_root(start: pathlib.Path) -> pathlib.Path:
    """Walk up from start to find the repository root."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return start.resolve()


def export_openapi() -> None:
    """Export OpenAPI schema to shared/api/openapi.json."""
    schema = app.openapi()
    repo_root = _find_repo_root(pathlib.Path(__file__).parent)
    output_path = repo_root / "shared" / "api" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)


if __name__ == "__main__":
    settings = get_settings()
    export_openapi()
    uvicorn.run(
        "bookmarks_organizer.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=False,
    )
