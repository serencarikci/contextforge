from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    limit: int
    offset: int
    total: int


class PaginationResponse[T](BaseModel):
    items: list[T]
    pagination: PaginationMeta = Field(
        ...,
        description="Pagination metadata for the current page.",
    )


__all__ = ["PaginationMeta", "PaginationResponse"]
