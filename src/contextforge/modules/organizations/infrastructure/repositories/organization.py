"""SQLAlchemy implementation of the organization repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.identity_access.domain.enums import OrganizationStatus
from contextforge.modules.identity_access.infrastructure.models.membership import (
    OrganizationMembershipModel,
)
from contextforge.modules.organizations.domain.entities.organization import Organization
from contextforge.modules.organizations.infrastructure.models.organization import OrganizationModel


class SqlAlchemyOrganizationRepository:
    """Persists Organization aggregates using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        statement = select(OrganizationModel).where(OrganizationModel.id == organization_id)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_slug(self, slug: str) -> Organization | None:
        statement = select(OrganizationModel).where(OrganizationModel.slug == slug)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def add(self, entity: Organization) -> Organization:
        model = OrganizationModel(
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: Organization) -> Organization:
        statement = select(OrganizationModel).where(OrganizationModel.id == entity.id)
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.name = entity.name
        model.slug = entity.slug
        model.status = entity.status.value
        model.updated_at = entity.updated_at

        await self._session.flush()
        return self._to_entity(model)

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
        status: OrganizationStatus | None = None,
    ) -> tuple[list[Organization], int]:
        conditions = [OrganizationMembershipModel.user_id == user_id]
        if status is not None:
            conditions.append(OrganizationModel.status == status.value)

        count_statement = (
            select(func.count())
            .select_from(OrganizationModel)
            .join(
                OrganizationMembershipModel,
                OrganizationMembershipModel.organization_id == OrganizationModel.id,
            )
            .where(and_(*conditions))
        )
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            select(OrganizationModel)
            .join(
                OrganizationMembershipModel,
                OrganizationMembershipModel.organization_id == OrganizationModel.id,
            )
            .where(and_(*conditions))
            .order_by(OrganizationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models], total

    @staticmethod
    def _to_entity(model: OrganizationModel) -> Organization:
        return Organization(
            name=model.name,
            slug=model.slug,
            id=model.id,
            status=OrganizationStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
