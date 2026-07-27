from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.modules.chat.domain.enums import FeedbackCategory, FeedbackRating
from contextforge.shared.utilities.datetime import utc_now

MAX_COMMENT_LENGTH = 2000


def _validate_score(score: int | None) -> int | None:
    if score is None:
        return None
    if not (1 <= score <= 5):
        msg = "Feedback score must be between 1 and 5"
        raise ValueError(msg)
    return score


def _normalize_comment(comment: str | None) -> str | None:
    if comment is None:
        return None
    cleaned = comment.strip()
    if not cleaned:
        return None
    return cleaned[:MAX_COMMENT_LENGTH]


@dataclass(slots=True)
class MessageFeedback:
    message_id: UUID
    conversation_id: UUID
    organization_id: UUID
    user_id: UUID
    rating: FeedbackRating
    id: UUID = field(default_factory=uuid4)
    score: int | None = None
    category: FeedbackCategory | None = None
    comment: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.score = _validate_score(self.score)
        self.comment = _normalize_comment(self.comment)

    def update(
        self,
        *,
        rating: FeedbackRating,
        score: int | None = None,
        category: FeedbackCategory | None = None,
        comment: str | None = None,
    ) -> None:
        self.rating = rating
        self.score = _validate_score(score)
        self.category = category
        self.comment = _normalize_comment(comment)
        self.updated_at = utc_now()


__all__ = ["MAX_COMMENT_LENGTH", "MessageFeedback"]
