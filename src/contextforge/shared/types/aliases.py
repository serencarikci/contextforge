"""Common type aliases."""

from __future__ import annotations

from uuid import UUID

type JSONPrimitive = str | int | float | bool | None
type JSONValue = JSONPrimitive | list[JSONValue] | dict[str, JSONValue]
type EntityId = UUID
