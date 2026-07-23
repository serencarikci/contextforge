"""Unit tests for correlation ID helpers."""

from __future__ import annotations

import pytest

from contextforge.shared.utilities.correlation import (
    is_valid_correlation_id,
    resolve_correlation_id,
)


@pytest.mark.unit
def test_valid_correlation_id() -> None:
    value = "550e8400-e29b-41d4-a716-446655440000"
    assert is_valid_correlation_id(value) is True
    assert resolve_correlation_id(value) == value


@pytest.mark.unit
def test_invalid_correlation_id_generates_new() -> None:
    generated = resolve_correlation_id("not-a-uuid")
    assert is_valid_correlation_id(generated) is True
    assert generated != "not-a-uuid"


@pytest.mark.unit
def test_missing_correlation_id_generates_new() -> None:
    generated = resolve_correlation_id(None)
    assert is_valid_correlation_id(generated) is True


@pytest.mark.unit
@pytest.mark.parametrize("value", ["", "   ", "123", "gggggggg-gggg-gggg-gggg-gggggggggggg"])
def test_invalid_values(value: str) -> None:
    assert is_valid_correlation_id(value) is False
