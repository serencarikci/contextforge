"""Pagination helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PaginationParams:
    limit: int = 25
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 100:
            msg = "limit must be between 1 and 100"
            raise ValueError(msg)
        if self.offset < 0:
            msg = "offset must be >= 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: list[T]
    limit: int
    offset: int
    total: int
