from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import sqlalchemy as sa
from alembic import context


def existing_role_codes(
    connection: Any,
    roles_table: Any,
    *,
    fallback: Iterable[str],
) -> set[str]:
    if context.is_offline_mode():
        return set(fallback)
    result = connection.execute(sa.select(roles_table.c.code))
    if result is None:
        return set(fallback)
    return {row[0] for row in result.fetchall()}
