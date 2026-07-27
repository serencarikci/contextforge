"""Database-backed prompt slot overrides for PromptRegistry."""

from __future__ import annotations

from uuid import UUID

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork


class DatabasePromptOverrideSource:
    async def active_slot_contents(
        self,
        uow: SqlAlchemyUnitOfWork,
        *,
        organization_id: UUID,
        language: str,
    ) -> dict[str, str]:
        async with uow:
            templates = await uow.prompt_templates.list_active_overrides(organization_id, language)
        return {template.name.value: template.content for template in templates}


__all__ = ["DatabasePromptOverrideSource"]
