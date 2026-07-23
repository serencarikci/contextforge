"""Repository port for user persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from contextforge.modules.identity_access.domain.entities.user import User


class UserRepository(Protocol):
    """Port for persisting and loading User aggregates."""

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return the user with the given id, or None if missing."""
        ...

    async def get_by_email(self, email: str) -> User | None:
        """Return the user with the given normalized email, or None if missing."""
        ...

    async def add(self, entity: User) -> User:
        """Persist a new user and return the persisted entity."""
        ...

    async def update(self, entity: User) -> User:
        """Persist changes to an existing user and return the entity."""
        ...
