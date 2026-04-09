"""Shared test fixtures and configuration."""

import os

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear cached settings between tests."""
    from bookmarks_organizer.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings():
    """Return test settings."""
    from bookmarks_organizer.config import Settings

    return Settings(
        anthropic_api_key="test-key",
        backend_host="127.0.0.1",
        backend_port=8765,
    )
