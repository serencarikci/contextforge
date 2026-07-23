"""MinIO client used for readiness checks and document storage."""

from __future__ import annotations

import asyncio
import io
import re
import time
from typing import BinaryIO
from uuid import UUID

from minio import Minio

from contextforge.application.ports.health import DependencyCheckResult
from contextforge.domain.exceptions.base import DependencyUnavailableError, InfrastructureError
from contextforge.shared.config.settings import MinioSettings
from contextforge.shared.logging.setup import get_logger

logger = get_logger(__name__)

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class ObjectStorageError(InfrastructureError):
    """Raised when a MinIO object operation fails."""

    code = "OBJECT_STORAGE_ERROR"


class MinioClient:
    """MinIO wrapper with async-friendly readiness checks."""

    name = "minio"

    def __init__(self, settings: MinioSettings) -> None:
        self._settings = settings
        self._client = Minio(
            endpoint=settings.endpoint,
            access_key=settings.access_key.get_secret_value(),
            secret_key=settings.secret_key.get_secret_value(),
            secure=settings.secure,
            region=settings.region,
        )

    @property
    def client(self) -> Minio:
        return self._client

    async def verify(self) -> None:
        result = await self.check()
        if result.status != "up":
            raise DependencyUnavailableError(
                f"MinIO is unavailable: {result.detail or 'connection failed'}"
            )

    async def check(self) -> DependencyCheckResult:
        started = time.perf_counter()
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._client.bucket_exists, self._settings.bucket),
                timeout=self._settings.timeout_seconds,
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return DependencyCheckResult(name=self.name, status="up", latency_ms=latency_ms)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.warning("minio_readiness_failed", exc_info=exc)
            return DependencyCheckResult(
                name=self.name,
                status="down",
                latency_ms=latency_ms,
                detail="connection failed",
            )

    async def put_object(
        self,
        object_name: str,
        data: BinaryIO | bytes,
        length: int,
        content_type: str,
    ) -> None:
        """Upload an object to the configured bucket."""
        stream: BinaryIO = io.BytesIO(data) if isinstance(data, bytes) else data
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.put_object,
                    self._settings.bucket,
                    object_name,
                    stream,
                    length,
                    content_type=content_type,
                ),
                timeout=self._settings.timeout_seconds,
            )
        except Exception as exc:
            logger.warning("minio_put_object_failed", exc_info=exc)
            raise ObjectStorageError(f"Failed to upload object '{object_name}'.") from exc

    async def get_object(self, object_name: str) -> bytes:
        """Download an object's bytes from the configured bucket."""

        def _read() -> bytes:
            response = self._client.get_object(self._settings.bucket, object_name)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_read),
                timeout=self._settings.timeout_seconds,
            )
        except Exception as exc:
            logger.warning("minio_get_object_failed", exc_info=exc)
            raise ObjectStorageError(f"Failed to download object '{object_name}'.") from exc

    async def remove_object(self, object_name: str) -> None:
        """Delete an object from the configured bucket."""
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._client.remove_object, self._settings.bucket, object_name),
                timeout=self._settings.timeout_seconds,
            )
        except Exception as exc:
            logger.warning("minio_remove_object_failed", exc_info=exc)
            raise ObjectStorageError(f"Failed to remove object '{object_name}'.") from exc

    @staticmethod
    def build_object_key(
        organization_id: UUID,
        knowledge_space_id: UUID,
        document_id: UUID,
        filename: str,
    ) -> str:
        """Build a deterministic, tenant-scoped object key for a document.

        Format: ``{organization_id}/{knowledge_space_id}/{document_id}/{safe_filename}``.
        """
        safe_filename = _UNSAFE_FILENAME_CHARS.sub("_", filename.strip()) or "file"
        return f"{organization_id}/{knowledge_space_id}/{document_id}/{safe_filename}"

    async def close(self) -> None:

        logger.info("minio_client_closed")
