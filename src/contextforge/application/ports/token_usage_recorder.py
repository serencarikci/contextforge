"""Port for best-effort daily token usage rollups."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from contextforge.application.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork


class TokenUsageRecorderPort(Protocol):
    """Records prompt/completion token usage into the daily rollup table."""

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
        """Upsert a daily usage row. Must never raise into the caller path."""
        ...
