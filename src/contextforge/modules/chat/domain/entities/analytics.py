"""Append-only chat analytics event entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from contextforge.modules.chat.domain.enums import AnalyticsEventType
from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class ChatAnalyticsEvent:
    """A single notable chat-domain occurrence, recorded for reporting."""

    organization_id: UUID
    event_type: AnalyticsEventType
    id: UUID = field(default_factory=uuid4)
    conversation_id: UUID | None = None
    message_id: UUID | None = None
    user_id: UUID | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


__all__ = ["ChatAnalyticsEvent"]
