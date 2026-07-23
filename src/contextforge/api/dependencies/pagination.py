"""Shared pagination dependency for list endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

from contextforge.application.pagination import PaginationParams


def get_pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginationParams:
    """Parse and validate ``limit``/``offset`` query parameters."""
    return PaginationParams(limit=limit, offset=offset)


__all__ = ["get_pagination"]
