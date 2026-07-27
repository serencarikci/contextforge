from __future__ import annotations

import re
from uuid import UUID, uuid4

_CORRELATION_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def is_valid_correlation_id(value: str | None) -> bool:
    if value is None or not value.strip():
        return False
    if not _CORRELATION_ID_PATTERN.match(value.strip()):
        return False
    try:
        UUID(value.strip())
    except ValueError:
        return False
    return True


def resolve_correlation_id(incoming: str | None) -> str:
    if is_valid_correlation_id(incoming):
        assert incoming is not None
        return incoming.strip()
    return str(uuid4())
