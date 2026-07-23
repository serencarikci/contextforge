"""Unit tests for infrastructure readiness helpers with mocked clients."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from contextforge.infrastructure.cache.redis_client import RedisClient
from contextforge.infrastructure.database.session import DatabaseManager
from contextforge.infrastructure.object_storage.minio_client import MinioClient, ObjectStorageError
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
def test_minio_build_object_key_sanitizes_filename() -> None:
    org_id = uuid4()
    ks_id = uuid4()
    doc_id = uuid4()

    key = MinioClient.build_object_key(org_id, ks_id, doc_id, "report v1 (final).pdf")

    assert key == f"{org_id}/{ks_id}/{doc_id}/report_v1_final_.pdf"
    assert " " not in key
    assert "(" not in key


@pytest.mark.unit
def test_minio_build_object_key_falls_back_for_empty_filename() -> None:
    org_id, ks_id, doc_id = uuid4(), uuid4(), uuid4()
    key = MinioClient.build_object_key(org_id, ks_id, doc_id, "   ")
    assert key == f"{org_id}/{ks_id}/{doc_id}/file"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_minio_put_object_success_and_failure() -> None:
    client = MinioClient(MinioSettings())
    mock = MagicMock()
    client._client = mock

    await client.put_object("org/ks/doc/file.txt", b"hello", 5, "text/plain")
    mock.put_object.assert_called_once()

    mock.put_object.side_effect = RuntimeError("boom")
    with pytest.raises(ObjectStorageError):
        await client.put_object("org/ks/doc/file.txt", b"hello", 5, "text/plain")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_minio_get_object_success_and_failure() -> None:
    client = MinioClient(MinioSettings())
    mock = MagicMock()
    response = MagicMock()
    response.read.return_value = b"hello world"
    mock.get_object.return_value = response
    client._client = mock

    data = await client.get_object("org/ks/doc/file.txt")
    assert data == b"hello world"
    response.close.assert_called_once()
    response.release_conn.assert_called_once()

    mock.get_object.side_effect = RuntimeError("boom")
    with pytest.raises(ObjectStorageError):
        await client.get_object("org/ks/doc/file.txt")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_minio_remove_object_success_and_failure() -> None:
    client = MinioClient(MinioSettings())
    mock = MagicMock()
    client._client = mock

    await client.remove_object("org/ks/doc/file.txt")
    mock.remove_object.assert_called_once()

    mock.remove_object.side_effect = RuntimeError("boom")
    with pytest.raises(ObjectStorageError):
        await client.remove_object("org/ks/doc/file.txt")


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
