from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TokenUsageAggregate:
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    request_count: int
    estimated_cost: Decimal
    organization_id: UUID | None = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


__all__ = ["TokenUsageAggregate"]
