"""Token pricing table and cost calculation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from contextforge.shared.utilities.datetime import utc_now

TOKENS_PER_PRICE_UNIT = Decimal(1000)
COST_QUANTUM = Decimal("0.000001")
MAX_PRICE_PER_1K = Decimal("10000")


def _coerce_price(value: Decimal | float | int | str, field_name: str) -> Decimal:
    price = value if isinstance(value, Decimal) else Decimal(str(value))
    if price.is_nan() or price.is_infinite():
        msg = f"{field_name} must be a finite decimal"
        raise ValueError(msg)
    if price < 0 or price > MAX_PRICE_PER_1K:
        msg = f"{field_name} must be between 0 and {MAX_PRICE_PER_1K}"
        raise ValueError(msg)
    return price.quantize(COST_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_cost(value: Decimal) -> Decimal:
    """Round a monetary amount to the persisted precision."""
    return value.quantize(COST_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(slots=True)
class TokenPricing:
    """Price per 1,000 prompt/completion tokens for one provider/model pair.

    Rows are time-bounded: ``effective_from`` is inclusive and
    ``effective_to`` (when set) is exclusive, so historical usage keeps the
    price that applied when it was recorded.
    """

    provider: str
    model: str
    input_price_per_1k: Decimal
    output_price_per_1k: Decimal
    id: UUID = field(default_factory=uuid4)
    currency: str = "USD"
    effective_from: datetime = field(default_factory=utc_now)
    effective_to: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.provider = self._validate_token(self.provider, "provider")
        self.model = self._validate_token(self.model, "model")
        self.currency = self._validate_currency(self.currency)
        self.input_price_per_1k = _coerce_price(self.input_price_per_1k, "input_price_per_1k")
        self.output_price_per_1k = _coerce_price(self.output_price_per_1k, "output_price_per_1k")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            msg = "effective_to must be after effective_from"
            raise ValueError(msg)

    @staticmethod
    def _validate_token(value: str, field_name: str) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 200:
            msg = f"TokenPricing {field_name} must be between 1 and 200 characters"
            raise ValueError(msg)
        return cleaned

    @staticmethod
    def _validate_currency(currency: str) -> str:
        cleaned = currency.strip().upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            msg = "Currency must be a 3-letter ISO code"
            raise ValueError(msg)
        return cleaned

    def estimate_cost(self, *, prompt_tokens: int, completion_tokens: int) -> Decimal:
        """Cost for a token split, rounded to the persisted precision."""
        if prompt_tokens < 0 or completion_tokens < 0:
            msg = "Token counts must be non-negative"
            raise ValueError(msg)
        prompt_cost = (Decimal(prompt_tokens) / TOKENS_PER_PRICE_UNIT) * self.input_price_per_1k
        completion_cost = (
            Decimal(completion_tokens) / TOKENS_PER_PRICE_UNIT
        ) * self.output_price_per_1k
        return quantize_cost(prompt_cost + completion_cost)

    def supersede(self, moment: datetime) -> None:
        """Close this price row so a newer one can take over at ``moment``."""
        if moment <= self.effective_from:
            msg = "A pricing row cannot be superseded before it became effective"
            raise ValueError(msg)
        self.effective_to = moment
        self.updated_at = utc_now()


def estimate_cost(
    pricing: TokenPricing | None,
    *,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal:
    """Cost helper that treats a missing price row as zero cost."""
    if pricing is None:
        return Decimal("0")
    return pricing.estimate_cost(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)


__all__ = [
    "COST_QUANTUM",
    "MAX_PRICE_PER_1K",
    "TOKENS_PER_PRICE_UNIT",
    "TokenPricing",
    "estimate_cost",
    "quantize_cost",
]
