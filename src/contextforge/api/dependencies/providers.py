"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.application.services.health_service import HealthService
from contextforge.application.services.system_info_service import SystemInfoService
from contextforge.infrastructure.cache.redis_client import RedisClient
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.infrastructure.object_storage.minio_client import MinioClient
from contextforge.infrastructure.repositories.system_metadata import (
    SqlAlchemySystemMetadataRepository,
)
from contextforge.infrastructure.vector_store.qdrant_client import QdrantHealthClient
from contextforge.shared.config.settings import Settings


def get_settings_dependency(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


def get_database(request: Request) -> DatabaseManager:
    return request.app.state.database  # type: ignore[no-any-return]


async def get_db_session(
    database: Annotated[DatabaseManager, Depends(get_database)],
) -> AsyncIterator[AsyncSession]:
    async with database.session() as session:
        yield session


def get_system_metadata_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SqlAlchemySystemMetadataRepository:
    return SqlAlchemySystemMetadataRepository(session)


def get_health_service(request: Request) -> HealthService:
    database: DatabaseManager = request.app.state.database
    redis_client: RedisClient = request.app.state.redis_client
    qdrant_client: QdrantHealthClient = request.app.state.qdrant_client
    minio_client: MinioClient = request.app.state.minio_client
    return HealthService(
        checkers=[database, redis_client, qdrant_client, minio_client],
    )


def get_system_info_service(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> SystemInfoService:
    return SystemInfoService(settings)
