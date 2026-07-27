"""Daily token usage rollup ORM model."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TokenUsageDailyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One (organization, day, provider, model) usage bucket."""

    __tablename__ = "token_usage_daily"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "day",
            "provider",
            "model",
            name="uq_token_usage_daily_org_day_provider_model",
        ),
        Index("ix_token_usage_daily_organization_day", "organization_id", "day"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    provider: Mapped[str] = mapped_column(String(200), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0")
    )

    def __repr__(self) -> str:
        return (
            f"TokenUsageDailyModel(id={self.id!s}, organization_id={self.organization_id!s}, "
            f"day={self.day!s})"
        )
