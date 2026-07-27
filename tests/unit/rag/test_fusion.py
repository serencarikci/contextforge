"""Unit tests for hybrid fusion helpers."""

from __future__ import annotations

from uuid import uuid4

import pytest

from contextforge.modules.rag.domain.fusion import (
    estimate_page_from_span,
    min_max_normalize,
    reciprocal_rank_fusion,
    weighted_fuse,
)


@pytest.mark.unit
def test_min_max_normalize_and_weighted_fuse() -> None:
    a, b = uuid4(), uuid4()
    dense = {a: 0.2, b: 0.8}
    lexical = {a: 10.0, b: 0.0}
    fused = weighted_fuse(dense, lexical, dense_weight=0.7, lexical_weight=0.3)
    assert fused[b] > fused[a]
    assert set(min_max_normalize(dense)) == {a, b}


@pytest.mark.unit
def test_rrf_and_page_estimation() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    scores = reciprocal_rank_fusion([[a, b, c], [b, a]])
    assert scores[b] >= scores[a]
    assert estimate_page_from_span(char_start=0, char_end=100, page_count=1) == 1
    assert estimate_page_from_span(char_start=4000, char_end=4500, page_count=5) >= 2
