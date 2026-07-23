"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest

# Ensure test environment defaults before settings are imported by the app.
os.environ.setdefault("CONTEXTFORGE_APP__ENVIRONMENT", "test")
os.environ.setdefault("CONTEXTFORGE_LOGGING__LEVEL", "WARNING")
os.environ.setdefault("CONTEXTFORGE_LOGGING__FORMAT", "console")
os.environ.setdefault("CONTEXTFORGE_SECURITY__SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("CONTEXTFORGE_API__DOCS_ENABLED", "true")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    from contextforge.shared.config.settings import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()
