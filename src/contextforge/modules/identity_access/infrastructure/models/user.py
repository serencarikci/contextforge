"""User ORM model."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from contextforge.modules.identity_access.domain.enums import PreferredLanguage, UserStatus


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Platform-wide user account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=UserStatus.ACTIVE.value)
    preferred_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default=PreferredLanguage.EN.value
    )
    is_platform_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    def __repr__(self) -> str:
        return f"UserModel(id={self.id!s}, email={self.email!r})"
