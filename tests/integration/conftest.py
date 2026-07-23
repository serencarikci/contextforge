"""Integration test fixtures."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.bootstrap.app_factory import create_app
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.shared.config.settings import Settings, clear_settings_cache


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    os.environ.setdefault("CONTEXTFORGE_APP__ENVIRONMENT", "test")
    os.environ.setdefault("CONTEXTFORGE_POSTGRES__HOST", "localhost")
    os.environ.setdefault("CONTEXTFORGE_POSTGRES__PORT", "5432")
    os.environ.setdefault("CONTEXTFORGE_POSTGRES__USER", "contextforge")
    os.environ.setdefault("CONTEXTFORGE_POSTGRES__PASSWORD", "contextforge_dev_password")
    os.environ.setdefault("CONTEXTFORGE_POSTGRES__DATABASE", "contextforge")
    os.environ.setdefault("CONTEXTFORGE_REDIS__URL", "redis://localhost:6379/0")
    os.environ.setdefault("CONTEXTFORGE_QDRANT__URL", "http://localhost:6333")
    os.environ.setdefault("CONTEXTFORGE_MINIO__ENDPOINT", "localhost:9000")
    os.environ.setdefault("CONTEXTFORGE_MINIO__ACCESS_KEY", "contextforge_minio")
    os.environ.setdefault("CONTEXTFORGE_MINIO__SECRET_KEY", "contextforge_minio_secret")
    os.environ.setdefault("CONTEXTFORGE_MINIO__BUCKET", "contextforge-documents")
    os.environ.setdefault("CONTEXTFORGE_MINIO__SECURE", "false")
    clear_settings_cache()
    return Settings()


@pytest.fixture
def api_client(integration_settings: Settings) -> TestClient:
    clear_settings_cache()
    app = create_app(integration_settings)
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def db_manager(integration_settings: Settings) -> DatabaseManager:
    manager = DatabaseManager(integration_settings.postgres)
    yield manager
    await manager.dispose()


@pytest_asyncio.fixture
async def db_session(db_manager: DatabaseManager) -> AsyncSession:
    async with db_manager.session_factory() as session:
        yield session
        await session.rollback()
