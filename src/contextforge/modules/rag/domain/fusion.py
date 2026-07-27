from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID


def min_max_normalize(scores: Mapping[UUID, float]) -> dict[UUID, float]:
    if not scores:
        return {}
    values = list(scores.values())
    low = min(values)
    high = max(values)
    if high <= low:
        return {key: 1.0 for key in scores}
    span = high - low
    return {key: (value - low) / span for key, value in scores.items()}


def weighted_fuse(
    dense_scores: Mapping[UUID, float],
    lexical_scores: Mapping[UUID, float],
    *,
    dense_weight: float,
    lexical_weight: float,
) -> dict[UUID, float]:
    dense_norm = min_max_normalize(dense_scores)
    lexical_norm = min_max_normalize(lexical_scores)
    keys = set(dense_norm) | set(lexical_norm)
    weight_sum = dense_weight + lexical_weight
    if weight_sum <= 0:
        weight_sum = 1.0
    fused: dict[UUID, float] = {}
    for key in keys:
        fused[key] = (
            dense_weight * dense_norm.get(key, 0.0) + lexical_weight * lexical_norm.get(key, 0.0)
        ) / weight_sum
    return fused


def reciprocal_rank_fusion(
    ranked_lists: list[list[UUID]],
    *,
    k: int = 60,
) -> dict[UUID, float]:
    scores: dict[UUID, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return scores


def estimate_page_from_span(
    *,
    char_start: int | None,
    char_end: int | None,
    page_count: int | None,
) -> int | None:
    if page_count is None or page_count < 1:
        return None
    if page_count == 1:
        return 1
    if char_start is None:
        return None
    if char_end is not None and char_end > char_start:
        page = (char_start // 1800) + 1
        return max(1, min(page_count, page))
    page = (char_start // 1800) + 1
    return max(1, min(page_count, page))


__all__ = [
    "estimate_page_from_span",
    "min_max_normalize",
    "reciprocal_rank_fusion",
    "weighted_fuse",
]
