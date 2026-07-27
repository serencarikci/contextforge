"""Chat message and citation entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.domain.exceptions.identity import InvalidResourceStateError
from contextforge.modules.chat.domain.enums import MessageRole, MessageStatus
from contextforge.shared.utilities.datetime import utc_now

MAX_CONTENT_LENGTH = 32_000


@dataclass(slots=True)
class ChatMessage:
    """A single turn in a conversation."""

    conversation_id: UUID
    organization_id: UUID
    role: MessageRole
    content: str
    sequence_no: int
    id: UUID = field(default_factory=uuid4)
    status: MessageStatus = MessageStatus.COMPLETED
    language: str | None = None
    parent_message_id: UUID | None = None
    model_name: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    retrieval_ms: int = 0
    error_code: str | None = None
    error_message: str | None = None
    idempotency_key: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.sequence_no < 0:
            msg = "Message sequence_no must be >= 0"
            raise ValueError(msg)
        if len(self.content) > MAX_CONTENT_LENGTH:
            msg = f"Message content exceeds the maximum length of {MAX_CONTENT_LENGTH} characters"
            raise ValueError(msg)

    def mark_streaming(self) -> None:
        self.status = MessageStatus.STREAMING
        self.updated_at = utc_now()

    def append_delta(self, delta: str) -> None:
        if self.status not in {MessageStatus.PENDING, MessageStatus.STREAMING}:
            raise InvalidResourceStateError("Message is not currently streaming.")
        self.content = f"{self.content}{delta}"
        self.updated_at = utc_now()

    def mark_completed(
        self,
        *,
        content: str | None = None,
        model_name: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: int = 0,
        retrieval_ms: int = 0,
        language: str | None = None,
    ) -> None:
        if content is not None:
            self.content = content
        if model_name is not None:
            self.model_name = model_name
        if language is not None:
            self.language = language
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.latency_ms = latency_ms
        self.retrieval_ms = retrieval_ms
        self.status = MessageStatus.COMPLETED
        self.error_code = None
        self.error_message = None
        self.updated_at = utc_now()

    def mark_failed(self, *, error_code: str, error_message: str) -> None:
        self.status = MessageStatus.FAILED
        self.error_code = error_code
        self.error_message = error_message[:2000]
        self.updated_at = utc_now()

    def mark_cancelled(self) -> None:
        self.status = MessageStatus.CANCELLED
        self.updated_at = utc_now()


@dataclass(slots=True)
class MessageCitation:
    """A single grounding citation attached to an assistant message."""

    message_id: UUID
    organization_id: UUID
    document_id: UUID
    document_title: str
    chunk_id: UUID
    knowledge_space_id: UUID
    snippet: str
    rank: int
    id: UUID = field(default_factory=uuid4)
    page: int | None = None
    chunk_index: int | None = None


__all__ = ["MAX_CONTENT_LENGTH", "ChatMessage", "MessageCitation"]
