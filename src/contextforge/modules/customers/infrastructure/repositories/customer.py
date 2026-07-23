"""SQLAlchemy implementation of the customer repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.customers.domain.entities.customer import Customer
from contextforge.modules.customers.infrastructure.models.customer import CustomerModel
from contextforge.modules.identity_access.domain.enums import CustomerStatus


class SqlAlchemyCustomerRepository:
    """Persists Customer aggregates using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, organization_id: UUID, customer_id: UUID) -> Customer | None:
        statement = select(CustomerModel).where(
            CustomerModel.id == customer_id,
            CustomerModel.organization_id == organization_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_code(self, organization_id: UUID, code: str) -> Customer | None:
        statement = select(CustomerModel).where(
            CustomerModel.organization_id == organization_id,
            CustomerModel.code == code,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def add(self, entity: Customer) -> Customer:
        model = CustomerModel(
            id=entity.id,
            organization_id=entity.organization_id,
            name=entity.name,
            code=entity.code,
            description=entity.description,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            archived_at=entity.archived_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: Customer) -> Customer:
        statement = select(CustomerModel).where(CustomerModel.id == entity.id)
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.name = entity.name
        model.description = entity.description
        model.status = entity.status.value
        model.updated_at = entity.updated_at
        model.archived_at = entity.archived_at

        await self._session.flush()
        return self._to_entity(model)

    async def list(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        status: CustomerStatus | None = None,
        query: str | None = None,
    ) -> tuple[list[Customer], int]:
        conditions = [CustomerModel.organization_id == organization_id]
        if status is not None:
            conditions.append(CustomerModel.status == status.value)
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            conditions.append(CustomerModel.name.ilike(pattern) | CustomerModel.code.ilike(pattern))

        count_statement = select(func.count()).select_from(CustomerModel).where(and_(*conditions))
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            select(CustomerModel)
            .where(and_(*conditions))
            .order_by(CustomerModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models], total

    @staticmethod
    def _to_entity(model: CustomerModel) -> Customer:
        return Customer(
            organization_id=model.organization_id,
            name=model.name,
            code=model.code,
            id=model.id,
            description=model.description,
            status=CustomerStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            archived_at=model.archived_at,
        )
