"""Unit tests for pagination parameter validation."""

from __future__ import annotations

import pytest

from contextforge.application.pagination import Page, PaginationParams


@pytest.mark.unit
class TestPaginationParams:
    def test_defaults(self) -> None:
        params = PaginationParams()
        assert params.limit == 25
        assert params.offset == 0

    @pytest.mark.parametrize(("limit", "offset"), [(1, 0), (100, 0), (50, 1000)])
    def test_accepts_boundary_values(self, limit: int, offset: int) -> None:
        params = PaginationParams(limit=limit, offset=offset)
        assert params.limit == limit
        assert params.offset == offset

    @pytest.mark.parametrize("limit", [0, -1, 101, 1000])
    def test_rejects_out_of_range_limit(self, limit: int) -> None:
        with pytest.raises(ValueError, match="limit must be between 1 and 100"):
            PaginationParams(limit=limit)

    def test_rejects_negative_offset(self) -> None:
        with pytest.raises(ValueError, match="offset must be >= 0"):
            PaginationParams(offset=-1)

    def test_is_frozen(self) -> None:
        params = PaginationParams()
        with pytest.raises(AttributeError):
            params.limit = 50  # type: ignore[misc]


@pytest.mark.unit
class TestPage:
    def test_holds_items_and_metadata(self) -> None:
        page = Page(items=[1, 2, 3], limit=25, offset=0, total=3)
        assert page.items == [1, 2, 3]
        assert page.limit == 25
        assert page.offset == 0
        assert page.total == 3

    def test_supports_empty_page(self) -> None:
        page: Page[int] = Page(items=[], limit=25, offset=50, total=10)
        assert page.items == []
        assert page.offset == 50
