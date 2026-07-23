"""Permission ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, UUIDPrimaryKeyMixin
from contextforge.shared.utilities.datetime import utc_now


class PermissionModel(Base, UUIDPrimaryKeyMixin):
    """Fine-grained permission code in the RBAC catalog."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"PermissionModel(id={self.id!s}, code={self.code!r})"
