"""SystemMetadata ORM model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SystemMetadataModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persisted system metadata key/value record."""

    __tablename__ = "system_metadata"

    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"SystemMetadataModel(id={self.id!s}, key={self.key!r})"
