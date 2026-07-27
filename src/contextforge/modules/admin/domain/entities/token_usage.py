"""Daily token usage rollup entity used for cost analytics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from contextforge.modules.admin.domain.entities.token_pricing import quantize_cost
from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class TokenUsageDaily:
    """One (organization, day, provider, model) usage bucket.

    Rows are additive: the rollup upserts by incrementing counters so a
    best-effort recording path can never lose earlier usage.
    """

    organization_id: UUID
    day: date
    provider: str
    model: str
    id: UUID = field(default_factory=uuid4)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    request_count: int = 0
    estimated_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.provider = self._validate_token(self.provider, "provider")
        self.model = self._validate_token(self.model, "model")
        for name in ("prompt_tokens", "completion_tokens", "request_count"):
            if getattr(self, name) < 0:
                msg = f"TokenUsageDaily {name} must be non-negative"
                raise ValueError(msg)
        if self.estimated_cost < 0:
            msg = "TokenUsageDaily estimated_cost must be non-negative"
            raise ValueError(msg)
        self.estimated_cost = quantize_cost(self.estimated_cost)

    @staticmethod
    def _validate_token(value: str, field_name: str) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 200:
            msg = f"TokenUsageDaily {field_name} must be between 1 and 200 characters"
            raise ValueError(msg)
        return cleaned

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def accumulate(
        self,
        *,
        prompt_tokens: int,
        completion_tokens: int,
        request_count: int = 1,
        estimated_cost: Decimal | None = None,
    ) -> None:
        if prompt_tokens < 0 or completion_tokens < 0 or request_count < 0:
            msg = "Token usage increments must be non-negative"
            raise ValueError(msg)
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.request_count += request_count
        if estimated_cost is not None:
            if estimated_cost < 0:
                msg = "Token usage cost increments must be non-negative"
                raise ValueError(msg)
            self.estimated_cost = quantize_cost(self.estimated_cost + estimated_cost)
        self.updated_at = utc_now()


@dataclass(frozen=True, slots=True)
class TokenUsageAggregate:
    """Grouped usage totals returned by the analytics queries."""

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


__all__ = ["TokenUsageAggregate", "TokenUsageDaily"]
