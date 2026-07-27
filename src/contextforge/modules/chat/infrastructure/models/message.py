from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from contextforge.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from contextforge.modules.chat.domain.enums import MessageStatus


class ChatMessageModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_chat_messages_organization_idempotency_key",
        ),
        UniqueConstraint(
            "conversation_id", "sequence_no", name="uq_chat_messages_conversation_sequence"
        ),
        Index("ix_chat_messages_conversation_id_sequence_no", "conversation_id", "sequence_no"),
        Index("ix_chat_messages_organization_id_status", "organization_id", "status"),
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
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MessageStatus.COMPLETED.value
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_message_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="RESTRICT"),
        nullable=True,
    )
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retrieval_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return (
            f"ChatMessageModel(id={self.id!s}, conversation_id={self.conversation_id!s}, "
            f"role={self.role!r}, sequence_no={self.sequence_no})"
        )


class MessageCitationModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "message_citations"
    __table_args__ = (
        Index("ix_message_citations_message_id", "message_id"),
        Index("ix_message_citations_organization_id", "organization_id"),
    )

    message_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_title: Mapped[str] = mapped_column(String(200), nullable=False)
    chunk_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    knowledge_space_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_spaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"MessageCitationModel(id={self.id!s}, message_id={self.message_id!s})"
