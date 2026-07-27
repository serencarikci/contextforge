from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from contextforge.modules.chat.domain.enums import (
    ChatLanguagePreference,
    ConversationParticipantRole,
    ConversationStatus,
    FeedbackCategory,
    FeedbackRating,
    MessageRole,
    MessageStatus,
)


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    knowledge_space_ids: list[UUID] | None = None
    preferred_language: ChatLanguagePreference = ChatLanguagePreference.AUTO


class ConversationUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    pinned: bool | None = None
    preferred_language: ChatLanguagePreference | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    owner_user_id: UUID
    title: str
    status: ConversationStatus
    preferred_language: ChatLanguagePreference
    detected_language: str | None
    pinned: bool
    last_activity_at: datetime
    summary_text: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ConversationParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    user_id: UUID
    role: ConversationParticipantRole


class ParticipantAddRequest(BaseModel):
    user_id: UUID
    role: ConversationParticipantRole = ConversationParticipantRole.PARTICIPANT


class KnowledgeSpaceLinkRequest(BaseModel):
    knowledge_space_id: UUID


class KnowledgeSpaceLinkListResponse(BaseModel):
    knowledge_space_ids: list[UUID]


class MessageCitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    document_title: str
    chunk_id: UUID
    knowledge_space_id: UUID
    page: int | None
    chunk_index: int | None
    snippet: str
    rank: int


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: MessageRole
    status: MessageStatus
    content: str
    language: str | None
    sequence_no: int
    parent_message_id: UUID | None
    model_name: str | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    retrieval_ms: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    citations: list[MessageCitationResponse] = Field(default_factory=list)


class MessageSendRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32000)
    idempotency_key: str | None = Field(default=None, max_length=255)


class ChatAnswerResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


class MessageFeedbackRequest(BaseModel):
    rating: FeedbackRating
    score: int | None = Field(default=None, ge=1, le=5)
    category: FeedbackCategory | None = None
    comment: str | None = Field(default=None, max_length=2000)


class MessageFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message_id: UUID
    conversation_id: UUID
    user_id: UUID
    rating: FeedbackRating
    score: int | None
    category: FeedbackCategory | None
    comment: str | None
    created_at: datetime
    updated_at: datetime


class SuggestionsResponse(BaseModel):
    suggestions: list[str]


class ChatAnalyticsOverviewResponse(BaseModel):
    total_messages: int
    assistant_messages: int
    failed_messages: int
    avg_latency_ms: float
    avg_retrieval_ms: float
    total_prompt_tokens: int
    total_completion_tokens: int
    feedback_up_count: int
    feedback_down_count: int
    events_by_type: dict[str, int]


__all__ = [
    "ChatAnalyticsOverviewResponse",
    "ChatAnswerResponse",
    "ChatMessageResponse",
    "ConversationCreateRequest",
    "ConversationParticipantResponse",
    "ConversationResponse",
    "ConversationUpdateRequest",
    "KnowledgeSpaceLinkListResponse",
    "KnowledgeSpaceLinkRequest",
    "MessageCitationResponse",
    "MessageFeedbackRequest",
    "MessageFeedbackResponse",
    "MessageSendRequest",
    "ParticipantAddRequest",
    "SuggestionsResponse",
]
