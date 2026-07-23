"""Application lifespan management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from contextforge.infrastructure.cache.redis_client import RedisClient
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.infrastructure.object_storage.minio_client import MinioClient
from contextforge.infrastructure.vector_store.qdrant_client import QdrantHealthClient
from contextforge.shared.config.settings import Settings
from contextforge.shared.logging.setup import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down application resources."""
    settings: Settings = app.state.settings
    configure_logging(settings.logging, environment=settings.app.environment.value)

    logger.info(
        "application_starting",
        extra={
            "environment": settings.app.environment.value,
            "version": settings.app.version,
        },
    )

    database = DatabaseManager(settings.postgres)
    redis_client = RedisClient(settings.redis)
    qdrant_client = QdrantHealthClient(settings.qdrant)
    minio_client = MinioClient(settings.minio)

    app.state.database = database
    app.state.redis_client = redis_client
    app.state.qdrant_client = qdrant_client
    app.state.minio_client = minio_client

    logger.info("application_started")
    try:
        yield
    finally:
        logger.info("application_stopping")
        await minio_client.close()
        await qdrant_client.close()
        await redis_client.close()
        await database.dispose()
        logger.info("application_stopped")
