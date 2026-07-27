"""Token usage rollups, pricing, and cost analytics."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from contextforge.application.context.request_context import RequestContext
from contextforge.application.services.command_support import build_audit_event
from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from contextforge.modules.admin.domain.entities.token_pricing import TokenPricing, estimate_cost
from contextforge.modules.admin.domain.entities.token_usage import TokenUsageAggregate
from contextforge.shared.config.settings import AdminSettings
from contextforge.shared.logging.setup import get_logger
from contextforge.shared.utilities.datetime import utc_now

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TokenExport:
    content_type: str
    filename: str
    body: str


class TokenUsageService:
    def __init__(self, settings: AdminSettings) -> None:
        self._settings = settings

    async def record(
        self,
        uow: SqlAlchemyUnitOfWork,
        *,
        organization_id: UUID,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        if not self._settings.token_usage_rollup_enabled:
            return
        try:
            async with uow:
                pricing = await uow.token_pricing.get_effective(provider, model)
                cost = estimate_cost(
                    pricing, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
                )
                await uow.token_usage.increment(
                    organization_id=organization_id,
                    day=utc_now().date(),
                    provider=provider,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    estimated_cost=cost,
                )
        except Exception:
            logger.warning(
                "token_usage_rollup_failed",
                extra={"organization_id": str(organization_id)},
                exc_info=True,
            )

    async def list_tokens(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        days: int = 30,
    ) -> list[TokenUsageAggregate]:
        async with uow:
            ctx.require_permission("admin:usage")
            day_to = utc_now().date()
            day_from = day_to - timedelta(days=max(1, min(days, 365)))
            return await uow.token_usage.aggregate(
                ctx.organization_id, day_from=day_from, day_to=day_to
            )

    async def list_pricing(
        self, uow: SqlAlchemyUnitOfWork, ctx: RequestContext
    ) -> list[TokenPricing]:
        async with uow:
            ctx.require_permission("admin:usage")
            return await uow.token_pricing.list_all()

    async def upsert_pricing(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        provider: str,
        model: str,
        input_price_per_1k: Decimal,
        output_price_per_1k: Decimal,
        currency: str | None = None,
    ) -> TokenPricing:
        async with uow:
            ctx.require_permission("admin:usage")
            now = utc_now()
            existing = await uow.token_pricing.get_effective(provider, model, at=now)
            if existing is not None and existing.effective_to is None:
                existing.supersede(now)
                await uow.token_pricing.update(existing)
            pricing = TokenPricing(
                provider=provider,
                model=model,
                input_price_per_1k=input_price_per_1k,
                output_price_per_1k=output_price_per_1k,
                currency=currency or self._settings.token_pricing_currency,
                effective_from=now,
            )
            pricing = await uow.token_pricing.add(pricing)
            event = build_audit_event(
                ctx,
                action="token_pricing.upserted",
                resource_type="token_pricing",
                resource_id=pricing.id,
                metadata={"provider": provider, "model": model},
            )
            await uow.audit.add(event)
            return pricing

    async def export_tokens(
        self,
        uow: SqlAlchemyUnitOfWork,
        ctx: RequestContext,
        *,
        days: int = 30,
        export_format: str = "json",
    ) -> TokenExport:
        rows = await self.list_tokens(uow, ctx, days=days)
        fmt = export_format.lower().strip()
        if fmt == "csv":
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(
                [
                    "provider",
                    "model",
                    "prompt_tokens",
                    "completion_tokens",
                    "request_count",
                    "estimated_cost",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row.provider,
                        row.model,
                        row.prompt_tokens,
                        row.completion_tokens,
                        row.request_count,
                        str(row.estimated_cost),
                    ]
                )
            return TokenExport(
                content_type="text/csv",
                filename="token_usage.csv",
                body=buffer.getvalue(),
            )
        payload = [
            {
                "provider": row.provider,
                "model": row.model,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "request_count": row.request_count,
                "estimated_cost": str(row.estimated_cost),
            }
            for row in rows
        ]
        return TokenExport(
            content_type="application/json",
            filename="token_usage.json",
            body=json.dumps(payload, indent=2),
        )
