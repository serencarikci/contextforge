from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LlmProviderConfigModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "llm_provider_configs"
    __table_args__ = (
        Index(
            "uq_llm_provider_configs_global",
            "provider",
            "model",
            unique=True,
            postgresql_where=text("organization_id IS NULL"),
        ),
        Index(
            "uq_llm_provider_configs_organization",
            "organization_id",
            "provider",
            "model",
            unique=True,
            postgresql_where=text("organization_id IS NOT NULL"),
        ),
        Index("ix_llm_provider_configs_organization_id", "organization_id"),
    )

    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_key_hint: Mapped[str | None] = mapped_column(String(20), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    timeout_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=60.0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    rate_limit_rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return (
            f"LlmProviderConfigModel(id={self.id!s}, provider={self.provider!r}, "
            f"model={self.model!r})"
        )
