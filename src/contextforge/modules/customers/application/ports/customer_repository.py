"""Repository port for customer persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from contextforge.modules.customers.domain.entities.customer import Customer
from contextforge.modules.identity_access.domain.enums import CustomerStatus


class CustomerRepository(Protocol):
    """Port for persisting and loading Customer aggregates."""

    async def get(self, organization_id: UUID, customer_id: UUID) -> Customer | None:
        """Return the customer with the given id scoped to the organization."""
        ...

    async def get_by_code(self, organization_id: UUID, code: str) -> Customer | None:
        """Return the customer with the given code within the organization."""
        ...

    async def add(self, entity: Customer) -> Customer:
        """Persist a new customer and return the persisted entity."""
        ...

    async def update(self, entity: Customer) -> Customer:
        """Persist changes to an existing customer and return the entity."""
        ...

    async def list(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        status: CustomerStatus | None = None,
        query: str | None = None,
    ) -> tuple[list[Customer], int]:
        """Return a page of customers for the organization, plus total count."""
        ...
