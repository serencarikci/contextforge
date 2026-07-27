"""SQLAlchemy repository for daily token usage rollups."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.admin.domain.entities.token_usage import (
    TokenUsageAggregate,
    TokenUsageDaily,
)
from contextforge.modules.admin.infrastructure.models.token_usage import TokenUsageDailyModel
from contextforge.shared.utilities.datetime import utc_now


class SqlAlchemyTokenUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_day(
        self,
        organization_id: UUID,
        day: date,
        provider: str,
        model: str,
    ) -> TokenUsageDaily | None:
        result = await self._session.execute(
            select(TokenUsageDailyModel).where(
                and_(
                    TokenUsageDailyModel.organization_id == organization_id,
                    TokenUsageDailyModel.day == day,
                    TokenUsageDailyModel.provider == provider,
                    TokenUsageDailyModel.model == model,
                )
            )
        )
        model_row = result.scalar_one_or_none()
        return None if model_row is None else self._to_entity(model_row)

    async def increment(
        self,
        *,
        organization_id: UUID,
        day: date,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        request_count: int = 1,
        estimated_cost: Decimal,
    ) -> None:
        now = utc_now()
        statement = (
            pg_insert(TokenUsageDailyModel)
            .values(
                id=uuid4(),
                organization_id=organization_id,
                day=day,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                request_count=request_count,
                estimated_cost=estimated_cost,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_token_usage_daily_org_day_provider_model",
                set_={
                    "prompt_tokens": TokenUsageDailyModel.prompt_tokens + prompt_tokens,
                    "completion_tokens": TokenUsageDailyModel.completion_tokens + completion_tokens,
                    "request_count": TokenUsageDailyModel.request_count + request_count,
                    "estimated_cost": TokenUsageDailyModel.estimated_cost + estimated_cost,
                    "updated_at": now,
                },
            )
        )
        await self._session.execute(statement)

    async def list_range(
        self,
        organization_id: UUID,
        *,
        day_from: date,
        day_to: date,
    ) -> list[TokenUsageDaily]:
        result = await self._session.execute(
            select(TokenUsageDailyModel)
            .where(
                and_(
                    TokenUsageDailyModel.organization_id == organization_id,
                    TokenUsageDailyModel.day >= day_from,
                    TokenUsageDailyModel.day <= day_to,
                )
            )
            .order_by(TokenUsageDailyModel.day.asc(), TokenUsageDailyModel.provider.asc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def aggregate(
        self,
        organization_id: UUID,
        *,
        day_from: date | None = None,
        day_to: date | None = None,
    ) -> list[TokenUsageAggregate]:
        conditions = [TokenUsageDailyModel.organization_id == organization_id]
        if day_from is not None:
            conditions.append(TokenUsageDailyModel.day >= day_from)
        if day_to is not None:
            conditions.append(TokenUsageDailyModel.day <= day_to)
        statement = (
            select(
                TokenUsageDailyModel.provider,
                TokenUsageDailyModel.model,
                func.coalesce(func.sum(TokenUsageDailyModel.prompt_tokens), 0),
                func.coalesce(func.sum(TokenUsageDailyModel.completion_tokens), 0),
                func.coalesce(func.sum(TokenUsageDailyModel.request_count), 0),
                func.coalesce(func.sum(TokenUsageDailyModel.estimated_cost), 0),
            )
            .where(and_(*conditions))
            .group_by(TokenUsageDailyModel.provider, TokenUsageDailyModel.model)
            .order_by(TokenUsageDailyModel.provider.asc(), TokenUsageDailyModel.model.asc())
        )
        result = await self._session.execute(statement)
        rows = result.all()
        return [
            TokenUsageAggregate(
                provider=str(row[0]),
                model=str(row[1]),
                prompt_tokens=int(row[2]),
                completion_tokens=int(row[3]),
                request_count=int(row[4]),
                estimated_cost=Decimal(str(row[5])),
                organization_id=organization_id,
            )
            for row in rows
        ]

    async def total_for_day(self, organization_id: UUID, day: date) -> int:
        result = await self._session.execute(
            select(
                func.coalesce(
                    func.sum(
                        TokenUsageDailyModel.prompt_tokens + TokenUsageDailyModel.completion_tokens
                    ),
                    0,
                )
            ).where(
                and_(
                    TokenUsageDailyModel.organization_id == organization_id,
                    TokenUsageDailyModel.day == day,
                )
            )
        )
        return int(result.scalar_one())

    @staticmethod
    def _to_entity(model: TokenUsageDailyModel) -> TokenUsageDaily:
        return TokenUsageDaily(
            organization_id=model.organization_id,
            day=model.day,
            provider=model.provider,
            model=model.model,
            id=model.id,
            prompt_tokens=model.prompt_tokens,
            completion_tokens=model.completion_tokens,
            request_count=model.request_count,
            estimated_cost=model.estimated_cost,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
