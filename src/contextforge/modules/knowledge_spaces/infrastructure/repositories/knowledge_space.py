"""SQLAlchemy implementation of the knowledge space repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.identity_access.domain.enums import (
    KnowledgeSpaceAccessLevel,
    KnowledgeSpaceStatus,
    KnowledgeSpaceVisibility,
)
from contextforge.modules.knowledge_spaces.domain.entities.knowledge_space import (
    KnowledgeSpace,
    KnowledgeSpaceMembership,
)
from contextforge.modules.knowledge_spaces.infrastructure.models.knowledge_space import (
    KnowledgeSpaceModel,
)
from contextforge.modules.knowledge_spaces.infrastructure.models.knowledge_space_membership import (
    KnowledgeSpaceMembershipModel,
)


class SqlAlchemyKnowledgeSpaceRepository:
    """Persists KnowledgeSpace aggregates and their memberships using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, organization_id: UUID, knowledge_space_id: UUID) -> KnowledgeSpace | None:
        statement = select(KnowledgeSpaceModel).where(
            KnowledgeSpaceModel.id == knowledge_space_id,
            KnowledgeSpaceModel.organization_id == organization_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_slug(self, organization_id: UUID, slug: str) -> KnowledgeSpace | None:
        statement = select(KnowledgeSpaceModel).where(
            KnowledgeSpaceModel.organization_id == organization_id,
            KnowledgeSpaceModel.slug == slug,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def add(self, entity: KnowledgeSpace) -> KnowledgeSpace:
        model = KnowledgeSpaceModel(
            id=entity.id,
            organization_id=entity.organization_id,
            project_id=entity.project_id,
            name=entity.name,
            slug=entity.slug,
            description=entity.description,
            visibility=entity.visibility.value,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            archived_at=entity.archived_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: KnowledgeSpace) -> KnowledgeSpace:
        statement = select(KnowledgeSpaceModel).where(KnowledgeSpaceModel.id == entity.id)
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.name = entity.name
        model.description = entity.description
        model.visibility = entity.visibility.value
        model.status = entity.status.value
        model.updated_at = entity.updated_at
        model.archived_at = entity.archived_at

        await self._session.flush()
        return self._to_entity(model)

    async def list_organization_visible_ids(self, organization_id: UUID) -> set[UUID]:
        statement = select(KnowledgeSpaceModel.id).where(
            KnowledgeSpaceModel.organization_id == organization_id,
            KnowledgeSpaceModel.visibility == KnowledgeSpaceVisibility.ORGANIZATION.value,
            KnowledgeSpaceModel.status == KnowledgeSpaceStatus.ACTIVE.value,
        )
        result = await self._session.execute(statement)
        return set(result.scalars().all())

    async def add_membership(self, entity: KnowledgeSpaceMembership) -> KnowledgeSpaceMembership:
        model = KnowledgeSpaceMembershipModel(
            id=entity.id,
            organization_id=entity.organization_id,
            knowledge_space_id=entity.knowledge_space_id,
            membership_id=entity.membership_id,
            access_level=entity.access_level.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._membership_to_entity(model)

    async def get_membership(
        self,
        organization_id: UUID,
        knowledge_space_id: UUID,
        ks_membership_id: UUID,
    ) -> KnowledgeSpaceMembership | None:
        statement = select(KnowledgeSpaceMembershipModel).where(
            KnowledgeSpaceMembershipModel.id == ks_membership_id,
            KnowledgeSpaceMembershipModel.knowledge_space_id == knowledge_space_id,
            KnowledgeSpaceMembershipModel.organization_id == organization_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._membership_to_entity(model)

    async def get_membership_by_org_membership(
        self,
        organization_id: UUID,
        knowledge_space_id: UUID,
        membership_id: UUID,
    ) -> KnowledgeSpaceMembership | None:
        statement = select(KnowledgeSpaceMembershipModel).where(
            KnowledgeSpaceMembershipModel.knowledge_space_id == knowledge_space_id,
            KnowledgeSpaceMembershipModel.membership_id == membership_id,
            KnowledgeSpaceMembershipModel.organization_id == organization_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._membership_to_entity(model)

    async def update_membership(self, entity: KnowledgeSpaceMembership) -> KnowledgeSpaceMembership:
        statement = select(KnowledgeSpaceMembershipModel).where(
            KnowledgeSpaceMembershipModel.id == entity.id
        )
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.access_level = entity.access_level.value
        model.updated_at = entity.updated_at

        await self._session.flush()
        return self._membership_to_entity(model)

    async def delete_membership(
        self, organization_id: UUID, knowledge_space_id: UUID, ks_membership_id: UUID
    ) -> bool:
        statement = select(KnowledgeSpaceMembershipModel).where(
            KnowledgeSpaceMembershipModel.id == ks_membership_id,
            KnowledgeSpaceMembershipModel.knowledge_space_id == knowledge_space_id,
            KnowledgeSpaceMembershipModel.organization_id == organization_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def list_memberships(
        self,
        organization_id: UUID,
        knowledge_space_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[KnowledgeSpaceMembership], int]:
        conditions = [
            KnowledgeSpaceMembershipModel.organization_id == organization_id,
            KnowledgeSpaceMembershipModel.knowledge_space_id == knowledge_space_id,
        ]

        count_statement = (
            select(func.count()).select_from(KnowledgeSpaceMembershipModel).where(and_(*conditions))
        )
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            select(KnowledgeSpaceMembershipModel)
            .where(and_(*conditions))
            .order_by(KnowledgeSpaceMembershipModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._membership_to_entity(model) for model in models], total

    async def list_accessible_ids_for_membership(
        self, organization_id: UUID, membership_id: UUID
    ) -> set[UUID]:
        statement = select(KnowledgeSpaceMembershipModel.knowledge_space_id).where(
            KnowledgeSpaceMembershipModel.organization_id == organization_id,
            KnowledgeSpaceMembershipModel.membership_id == membership_id,
        )
        result = await self._session.execute(statement)
        return set(result.scalars().all())

    async def list(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        status: KnowledgeSpaceStatus | None = None,
        visibility: KnowledgeSpaceVisibility | None = None,
        project_id: UUID | None = None,
        query: str | None = None,
    ) -> tuple[list[KnowledgeSpace], int]:
        conditions = [KnowledgeSpaceModel.organization_id == organization_id]
        if status is not None:
            conditions.append(KnowledgeSpaceModel.status == status.value)
        if visibility is not None:
            conditions.append(KnowledgeSpaceModel.visibility == visibility.value)
        if project_id is not None:
            conditions.append(KnowledgeSpaceModel.project_id == project_id)
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            conditions.append(
                KnowledgeSpaceModel.name.ilike(pattern) | KnowledgeSpaceModel.slug.ilike(pattern)
            )

        count_statement = (
            select(func.count()).select_from(KnowledgeSpaceModel).where(and_(*conditions))
        )
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            select(KnowledgeSpaceModel)
            .where(and_(*conditions))
            .order_by(KnowledgeSpaceModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models], total

    @staticmethod
    def _to_entity(model: KnowledgeSpaceModel) -> KnowledgeSpace:
        return KnowledgeSpace(
            organization_id=model.organization_id,
            name=model.name,
            slug=model.slug,
            id=model.id,
            project_id=model.project_id,
            description=model.description,
            visibility=KnowledgeSpaceVisibility(model.visibility),
            status=KnowledgeSpaceStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            archived_at=model.archived_at,
        )

    @staticmethod
    def _membership_to_entity(
        model: KnowledgeSpaceMembershipModel,
    ) -> KnowledgeSpaceMembership:
        return KnowledgeSpaceMembership(
            organization_id=model.organization_id,
            knowledge_space_id=model.knowledge_space_id,
            membership_id=model.membership_id,
            access_level=KnowledgeSpaceAccessLevel(model.access_level),
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
