from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class ConversationMemory:
    conversation_id: UUID
    organization_id: UUID
    summary_text: str
    covered_until_sequence: int
    token_estimate: int
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def update(
        self,
        *,
        summary_text: str,
        covered_until_sequence: int,
        token_estimate: int,
    ) -> None:
        self.summary_text = summary_text
        self.covered_until_sequence = covered_until_sequence
        self.token_estimate = token_estimate
        self.updated_at = utc_now()


__all__ = ["ConversationMemory"]
