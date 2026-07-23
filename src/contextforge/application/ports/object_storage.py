"""Port for object storage (blob) operations used by application services."""

from __future__ import annotations

from typing import BinaryIO, Protocol
from uuid import UUID


class ObjectStoragePort(Protocol):
    """Port implemented by infrastructure clients that store file bytes."""

    async def put_object(
        self,
        object_name: str,
        data: BinaryIO | bytes,
        length: int,
        content_type: str,
    ) -> None:
        """Upload an object."""
        ...

    async def get_object(self, object_name: str) -> bytes:
        """Download an object's bytes."""
        ...

    async def remove_object(self, object_name: str) -> None:
        """Delete an object."""
        ...

    def build_object_key(
        self,
        organization_id: UUID,
        knowledge_space_id: UUID,
        document_id: UUID,
        filename: str,
    ) -> str:
        """Build a deterministic, tenant-scoped object key."""
        ...
