from __future__ import annotations

from typing import BinaryIO, Protocol
from uuid import UUID


class ObjectStoragePort(Protocol):
    async def put_object(
        self,
        object_name: str,
        data: BinaryIO | bytes,
        length: int,
        content_type: str,
    ) -> None: ...

    async def get_object(self, object_name: str) -> bytes: ...

    async def remove_object(self, object_name: str) -> None: ...

    def build_object_key(
        self,
        organization_id: UUID,
        knowledge_space_id: UUID,
        document_id: UUID,
        filename: str,
    ) -> str: ...
