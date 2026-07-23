"""SQLAlchemy implementation of the project repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.identity_access.domain.enums import PreferredLanguage, ProjectStatus
from contextforge.modules.projects.domain.entities.project import Project
from contextforge.modules.projects.infrastructure.models.project import ProjectModel


class SqlAlchemyProjectRepository:
    """Persists Project aggregates using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, organization_id: UUID, project_id: UUID) -> Project | None:
        statement = select(ProjectModel).where(
            ProjectModel.id == project_id,
            ProjectModel.organization_id == organization_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_key(self, organization_id: UUID, key: str) -> Project | None:
        statement = select(ProjectModel).where(
            ProjectModel.organization_id == organization_id,
            ProjectModel.key == key,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def add(self, entity: Project) -> Project:
        model = ProjectModel(
            id=entity.id,
            organization_id=entity.organization_id,
            customer_id=entity.customer_id,
            name=entity.name,
            key=entity.key,
            description=entity.description,
            status=entity.status.value,
            default_language=entity.default_language.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            archived_at=entity.archived_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: Project) -> Project:
        statement = select(ProjectModel).where(ProjectModel.id == entity.id)
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.customer_id = entity.customer_id
        model.name = entity.name
        model.description = entity.description
        model.status = entity.status.value
        model.default_language = entity.default_language.value
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
        status: ProjectStatus | None = None,
        customer_id: UUID | None = None,
        query: str | None = None,
    ) -> tuple[list[Project], int]:
        conditions = [ProjectModel.organization_id == organization_id]
        if status is not None:
            conditions.append(ProjectModel.status == status.value)
        if customer_id is not None:
            conditions.append(ProjectModel.customer_id == customer_id)
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            conditions.append(ProjectModel.name.ilike(pattern) | ProjectModel.key.ilike(pattern))

        count_statement = select(func.count()).select_from(ProjectModel).where(and_(*conditions))
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            select(ProjectModel)
            .where(and_(*conditions))
            .order_by(ProjectModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models], total

    @staticmethod
    def _to_entity(model: ProjectModel) -> Project:
        return Project(
            organization_id=model.organization_id,
            name=model.name,
            key=model.key,
            id=model.id,
            customer_id=model.customer_id,
            description=model.description,
            status=ProjectStatus(model.status),
            default_language=PreferredLanguage(model.default_language),
            created_at=model.created_at,
            updated_at=model.updated_at,
            archived_at=model.archived_at,
        )
