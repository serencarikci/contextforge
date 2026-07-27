from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.admin.domain.entities.token_pricing import TokenPricing
from contextforge.modules.admin.infrastructure.models.token_pricing import TokenPricingModel
from contextforge.shared.utilities.datetime import utc_now


class SqlAlchemyTokenPricingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, pricing_id: UUID) -> TokenPricing | None:
        result = await self._session.execute(
            select(TokenPricingModel).where(TokenPricingModel.id == pricing_id)
        )
        row = result.scalar_one_or_none()
        return None if row is None else self._to_entity(row)

    async def list_all(self) -> list[TokenPricing]:
        result = await self._session.execute(
            select(TokenPricingModel).order_by(
                TokenPricingModel.provider.asc(),
                TokenPricingModel.model.asc(),
                TokenPricingModel.effective_from.desc(),
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_effective(
        self, provider: str, model: str, *, at: datetime | None = None
    ) -> TokenPricing | None:
        moment = at or utc_now()
        result = await self._session.execute(
            select(TokenPricingModel)
            .where(
                and_(
                    TokenPricingModel.provider == provider,
                    TokenPricingModel.model == model,
                    TokenPricingModel.effective_from <= moment,
                    or_(
                        TokenPricingModel.effective_to.is_(None),
                        TokenPricingModel.effective_to > moment,
                    ),
                )
            )
            .order_by(TokenPricingModel.effective_from.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else self._to_entity(row)

    async def add(self, entity: TokenPricing) -> TokenPricing:
        model = TokenPricingModel(
            id=entity.id,
            provider=entity.provider,
            model=entity.model,
            input_price_per_1k=entity.input_price_per_1k,
            output_price_per_1k=entity.output_price_per_1k,
            currency=entity.currency,
            effective_from=entity.effective_from,
            effective_to=entity.effective_to,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, entity: TokenPricing) -> TokenPricing:
        result = await self._session.execute(
            select(TokenPricingModel).where(TokenPricingModel.id == entity.id)
        )
        model = result.scalar_one()
        model.input_price_per_1k = entity.input_price_per_1k
        model.output_price_per_1k = entity.output_price_per_1k
        model.currency = entity.currency
        model.effective_from = entity.effective_from
        model.effective_to = entity.effective_to
        model.updated_at = entity.updated_at
        await self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: TokenPricingModel) -> TokenPricing:
        return TokenPricing(
            provider=model.provider,
            model=model.model,
            input_price_per_1k=model.input_price_per_1k,
            output_price_per_1k=model.output_price_per_1k,
            id=model.id,
            currency=model.currency,
            effective_from=model.effective_from,
            effective_to=model.effective_to,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
