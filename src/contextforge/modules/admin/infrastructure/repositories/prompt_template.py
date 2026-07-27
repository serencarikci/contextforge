from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.admin.domain.entities.prompt_template import PromptTemplate
from contextforge.modules.admin.domain.enums import PromptLanguage, PromptTemplateName
from contextforge.modules.admin.infrastructure.models.prompt_template import PromptTemplateModel


class SqlAlchemyPromptTemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, template_id: UUID) -> PromptTemplate | None:
        result = await self._session.execute(
            select(PromptTemplateModel).where(PromptTemplateModel.id == template_id)
        )
        model = result.scalar_one_or_none()
        return None if model is None else self._to_entity(model)

    async def list_templates(
        self,
        *,
        organization_id: UUID | None = None,
        include_global: bool = True,
        language: str | None = None,
        name: str | None = None,
        active_only: bool = False,
    ) -> list[PromptTemplate]:
        conditions: list[ColumnElement[bool]] = []
        if organization_id is None:
            conditions.append(PromptTemplateModel.organization_id.is_(None))
        elif include_global:
            conditions.append(
                or_(
                    PromptTemplateModel.organization_id.is_(None),
                    PromptTemplateModel.organization_id == organization_id,
                )
            )
        else:
            conditions.append(PromptTemplateModel.organization_id == organization_id)
        if language is not None:
            conditions.append(PromptTemplateModel.language == language)
        if name is not None:
            conditions.append(PromptTemplateModel.name == name)
        if active_only:
            conditions.append(PromptTemplateModel.is_active.is_(True))

        statement = select(PromptTemplateModel)
        if conditions:
            statement = statement.where(and_(*conditions))
        statement = statement.order_by(
            PromptTemplateModel.name.asc(),
            PromptTemplateModel.language.asc(),
            PromptTemplateModel.version.desc(),
        )
        result = await self._session.execute(statement)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_active_overrides(
        self, organization_id: UUID, language: str
    ) -> list[PromptTemplate]:
        org_rows = await self.list_templates(
            organization_id=organization_id,
            include_global=False,
            language=language,
            active_only=True,
        )
        by_name = {row.name.value: row for row in org_rows}
        if len(by_name) < len(PromptTemplateName):
            global_rows = await self.list_templates(
                organization_id=None,
                include_global=False,
                language=language,
                active_only=True,
            )
            for row in global_rows:
                by_name.setdefault(row.name.value, row)
        return list(by_name.values())

    async def add(self, entity: PromptTemplate) -> PromptTemplate:
        model = PromptTemplateModel(
            id=entity.id,
            organization_id=entity.organization_id,
            name=entity.name.value,
            version=entity.version,
            language=entity.language.value,
            content=entity.content,
            is_active=entity.is_active,
            is_system=entity.is_system,
            created_by=entity.created_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: PromptTemplate) -> PromptTemplate:
        result = await self._session.execute(
            select(PromptTemplateModel).where(PromptTemplateModel.id == entity.id)
        )
        model = result.scalar_one()
        model.content = entity.content
        model.is_active = entity.is_active
        model.updated_at = entity.updated_at
        await self._session.flush()
        return self._to_entity(model)

    async def deactivate_siblings(self, entity: PromptTemplate) -> None:
        conditions = [
            PromptTemplateModel.name == entity.name.value,
            PromptTemplateModel.language == entity.language.value,
            PromptTemplateModel.id != entity.id,
            PromptTemplateModel.is_active.is_(True),
        ]
        if entity.organization_id is None:
            conditions.append(PromptTemplateModel.organization_id.is_(None))
        else:
            conditions.append(PromptTemplateModel.organization_id == entity.organization_id)
        await self._session.execute(
            update(PromptTemplateModel).where(and_(*conditions)).values(is_active=False)
        )

    async def delete(self, template_id: UUID) -> bool:
        result = await self._session.execute(
            select(PromptTemplateModel).where(PromptTemplateModel.id == template_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    @staticmethod
    def _to_entity(model: PromptTemplateModel) -> PromptTemplate:
        return PromptTemplate(
            name=PromptTemplateName(model.name),
            version=model.version,
            language=PromptLanguage(model.language),
            content=model.content,
            id=model.id,
            organization_id=model.organization_id,
            is_active=model.is_active,
            is_system=model.is_system,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
