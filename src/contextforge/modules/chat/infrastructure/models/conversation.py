from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from contextforge.modules.chat.domain.entities.conversation import DEFAULT_TITLE
from contextforge.modules.chat.domain.enums import (
    ChatLanguagePreference,
    ConversationParticipantRole,
    ConversationStatus,
)


class ConversationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        Index(
            "ix_conversations_org_owner_status_activity",
            "organization_id",
            "owner_user_id",
            "status",
            "last_activity_at",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default=DEFAULT_TITLE)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ConversationStatus.ACTIVE.value
    )
    preferred_language: Mapped[str] = mapped_column(
        String(8), nullable=False, default=ChatLanguagePreference.AUTO.value
    )
    detected_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"ConversationModel(id={self.id!s}, title={self.title!r})"


class ConversationParticipantModel(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "user_id", name="uq_conversation_participants_conversation_user"
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
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
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ConversationParticipantRole.PARTICIPANT.value
    )

    def __repr__(self) -> str:
        return (
            f"ConversationParticipantModel(id={self.id!s}, "
            f"conversation_id={self.conversation_id!s}, user_id={self.user_id!s})"
        )


class ConversationKnowledgeSpaceModel(Base):
    __tablename__ = "conversation_knowledge_spaces"

    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    knowledge_space_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_spaces.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    def __repr__(self) -> str:
        return (
            f"ConversationKnowledgeSpaceModel(conversation_id={self.conversation_id!s}, "
            f"knowledge_space_id={self.knowledge_space_id!s})"
        )
