"""Token pricing ORM model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TokenPricingModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Price per 1,000 tokens for one provider/model pair over a time window."""

    __tablename__ = "token_pricing"
    __table_args__ = (
        Index(
            "ix_token_pricing_provider_model_effective",
            "provider",
            "model",
            "effective_from",
        ),
    )

    provider: Mapped[str] = mapped_column(String(200), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    input_price_per_1k: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    output_price_per_1k: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"TokenPricingModel(id={self.id!s}, provider={self.provider!r}, model={self.model!r})"
        )
