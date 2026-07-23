"""SQLAlchemy implementation of the user repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.identity_access.domain.entities.user import User
from contextforge.modules.identity_access.domain.enums import PreferredLanguage, UserStatus
from contextforge.modules.identity_access.infrastructure.models.user import UserModel


class SqlAlchemyUserRepository:
    """Persists User aggregates using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        statement = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_email(self, email: str) -> User | None:
        statement = select(UserModel).where(UserModel.email == email.strip().lower())
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def add(self, entity: User) -> User:
        model = UserModel(
            id=entity.id,
            email=entity.email,
            display_name=entity.display_name,
            status=entity.status.value,
            preferred_language=entity.preferred_language.value,
            is_platform_admin=entity.is_platform_admin,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: User) -> User:
        statement = select(UserModel).where(UserModel.id == entity.id)
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.email = entity.email
        model.display_name = entity.display_name
        model.status = entity.status.value
        model.preferred_language = entity.preferred_language.value
        model.is_platform_admin = entity.is_platform_admin
        model.updated_at = entity.updated_at

        await self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            email=model.email,
            display_name=model.display_name,
            id=model.id,
            status=UserStatus(model.status),
            preferred_language=PreferredLanguage(model.preferred_language),
            is_platform_admin=model.is_platform_admin,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
