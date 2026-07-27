from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from contextforge.shared.utilities.datetime import utc_now


@dataclass(slots=True)
class SystemMetadata:
    key: str
    value: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.key or not self.key.strip():
            msg = "SystemMetadata key must be a non-empty string"
            raise ValueError(msg)
        self.key = self.key.strip()

    def update_value(self, value: dict[str, Any]) -> None:
        self.value = value
        self.updated_at = utc_now()
