"""Message feedback ORM model."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MessageFeedbackModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One user's feedback on a single assistant message."""

    __tablename__ = "message_feedback"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_feedback_message_user"),
        CheckConstraint(
            "score IS NULL OR (score >= 1 AND score <= 5)", name="ck_message_feedback_score_range"
        ),
        Index("ix_message_feedback_conversation_id", "conversation_id"),
        Index("ix_message_feedback_organization_id", "organization_id"),
    )

    message_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="RESTRICT"),
        nullable=False,
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
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rating: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"MessageFeedbackModel(id={self.id!s}, message_id={self.message_id!s})"
