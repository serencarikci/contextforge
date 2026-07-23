"""Repository port for system metadata persistence."""

from __future__ import annotations

from typing import Protocol

from contextforge.domain.entities.system_metadata import SystemMetadata


class SystemMetadataRepository(Protocol):
    """Port for persisting and loading system metadata."""

    async def get_by_key(self, key: str) -> SystemMetadata | None:
        """Return metadata for the given key, or None if missing."""
        ...

    async def upsert(self, entity: SystemMetadata) -> SystemMetadata:
        """Insert or update a metadata record and return the persisted entity."""
        ...

    async def delete_by_key(self, key: str) -> bool:
        """Delete a metadata record by key. Returns True if a row was deleted."""
        ...
