"""Unit tests for infrastructure readiness helpers with mocked clients."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from contextforge.infrastructure.cache.redis_client import RedisClient
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.infrastructure.object_storage.minio_client import MinioClient
from contextforge.infrastructure.vector_store.qdrant_client import QdrantHealthClient
from contextforge.shared.config.settings import (
    MinioSettings,
    PostgresSettings,
    QdrantSettings,
    RedisSettings,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_check_up_and_down(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RedisClient(RedisSettings(url="redis://localhost:6379/0"))
    mock_redis = MagicMock()

    async def ping_ok() -> bool:
        return True

    mock_redis.ping = ping_ok
    client._client = mock_redis
    result = await client.check()
    assert result.status == "up"

    async def ping_fail() -> bool:
        raise ConnectionError("down")

    mock_redis.ping = ping_fail
    result = await client.check()
    assert result.status == "down"

    async def close() -> None:
        return None

    mock_redis.close = close
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_qdrant_check_up_and_down(monkeypatch: pytest.MonkeyPatch) -> None:
    client = QdrantHealthClient(QdrantSettings(url="http://localhost:6333"))
    mock = MagicMock()
    mock.get_collections.return_value = []
    client._client = mock
    assert (await client.check()).status == "up"

    mock.get_collections.side_effect = RuntimeError("down")
    assert (await client.check()).status == "down"
    mock.close.return_value = None
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_minio_check_up_and_down() -> None:
    client = MinioClient(MinioSettings())
    mock = MagicMock()
    mock.bucket_exists.return_value = True
    client._client = mock
    assert (await client.check()).status == "up"

    mock.bucket_exists.side_effect = RuntimeError("down")
    assert (await client.check()).status == "down"
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_database_check_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = DatabaseManager(PostgresSettings())

    class _Conn:
        async def execute(self, _statement: Any) -> None:
            return None

        async def __aenter__(self) -> _Conn:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    class _Engine:
        def connect(self) -> _Conn:
            return _Conn()

        async def dispose(self) -> None:
            return None

    manager._engine = _Engine()  # type: ignore[assignment]
    assert (await manager.check()).status == "up"

    class _BadEngine:
        def connect(self) -> Any:
            raise ConnectionError("db down")

        async def dispose(self) -> None:
            return None

    manager._engine = _BadEngine()  # type: ignore[assignment]
    assert (await manager.check()).status == "down"
    await manager.dispose()
