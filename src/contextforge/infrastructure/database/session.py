"""Async database engine and session management."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from contextforge.application.ports.health import DependencyCheckResult
from contextforge.domain.exceptions.base import DependencyUnavailableError
from contextforge.shared.config.settings import PostgresSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages the SQLAlchemy async engine and session factory."""

    name = "postgresql"

    def __init__(self, settings: PostgresSettings) -> None:
        self._settings = settings
        self._engine: AsyncEngine = create_async_engine(
            settings.async_dsn,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            echo=settings.echo,
            pool_pre_ping=True,
            connect_args={"timeout": settings.connect_timeout_seconds},
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    async def verify(self) -> None:
        """Verify the database connection can be established."""
        result = await self.check()
        if result.status != "up":
            raise DependencyUnavailableError(
                f"PostgreSQL is unavailable: {result.detail or 'connection failed'}"
            )

    async def check(self) -> DependencyCheckResult:
        """Probe PostgreSQL readiness."""
        started = time.perf_counter()
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return DependencyCheckResult(
                name=self.name,
                status="up",
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.warning("postgresql_readiness_failed", exc_info=exc)
            return DependencyCheckResult(
                name=self.name,
                status="down",
                latency_ms=latency_ms,
                detail="connection failed",
            )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Provide a transactional session with explicit commit/rollback."""
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def dispose(self) -> None:
        """Dispose of the engine connection pool."""
        await self._engine.dispose()
        logger.info("database_engine_disposed")
