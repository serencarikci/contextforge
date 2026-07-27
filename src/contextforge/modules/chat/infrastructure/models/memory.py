"""Conversation memory ORM model."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConversationMemoryModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A durable, compacted summary of a conversation's history."""

    __tablename__ = "conversation_memories"
    __table_args__ = (
        Index(
            "ix_conversation_memories_conversation_id",
            "conversation_id",
            unique=True,
        ),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    covered_until_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"ConversationMemoryModel(id={self.id!s}, conversation_id={self.conversation_id!s})"
