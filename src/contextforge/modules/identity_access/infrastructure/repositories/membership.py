"""SQLAlchemy implementation of the organization membership repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.identity_access.domain.entities.membership import (
    OrganizationMembership,
)
from contextforge.modules.identity_access.domain.enums import MembershipStatus
from contextforge.modules.identity_access.infrastructure.models.membership import (
    OrganizationMembershipModel,
)
from contextforge.modules.identity_access.infrastructure.models.user import UserModel


class SqlAlchemyMembershipRepository:
    """Persists OrganizationMembership aggregates using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, organization_id: UUID, membership_id: UUID
    ) -> OrganizationMembership | None:
        statement = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.id == membership_id,
            OrganizationMembershipModel.organization_id == organization_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_org_and_user(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership | None:
        statement = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.organization_id == organization_id,
            OrganizationMembershipModel.user_id == user_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def add(self, entity: OrganizationMembership) -> OrganizationMembership:
        model = OrganizationMembershipModel(
            id=entity.id,
            organization_id=entity.organization_id,
            user_id=entity.user_id,
            status=entity.status.value,
            joined_at=entity.joined_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: OrganizationMembership) -> OrganizationMembership:
        statement = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.id == entity.id
        )
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.status = entity.status.value
        model.joined_at = entity.joined_at
        model.updated_at = entity.updated_at

        await self._session.flush()
        return self._to_entity(model)

    async def list_for_organization(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        status: MembershipStatus | None = None,
        query: str | None = None,
    ) -> tuple[list[OrganizationMembership], int]:
        conditions = [OrganizationMembershipModel.organization_id == organization_id]
        if status is not None:
            conditions.append(OrganizationMembershipModel.status == status.value)

        needs_user_join = False
        if query and query.strip():
            needs_user_join = True
            pattern = f"%{query.strip()}%"
            conditions.append(
                or_(
                    UserModel.email.ilike(pattern),
                    UserModel.display_name.ilike(pattern),
                )
            )

        count_statement = select(func.count()).select_from(OrganizationMembershipModel)
        statement = select(OrganizationMembershipModel)
        if needs_user_join:
            count_statement = count_statement.join(
                UserModel, UserModel.id == OrganizationMembershipModel.user_id
            )
            statement = statement.join(
                UserModel, UserModel.id == OrganizationMembershipModel.user_id
            )

        count_statement = count_statement.where(and_(*conditions))
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            statement.where(and_(*conditions))
            .order_by(OrganizationMembershipModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models], total

    @staticmethod
    def _to_entity(model: OrganizationMembershipModel) -> OrganizationMembership:
        return OrganizationMembership(
            organization_id=model.organization_id,
            user_id=model.user_id,
            id=model.id,
            status=MembershipStatus(model.status),
            joined_at=model.joined_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
