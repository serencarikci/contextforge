"""Unit tests for domain entity behavior."""

from __future__ import annotations

import pytest

from contextforge.domain.entities.system_metadata import SystemMetadata


@pytest.mark.unit
def test_system_metadata_rejects_empty_key() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        SystemMetadata(key="  ", value={"a": 1})


@pytest.mark.unit
def test_system_metadata_update_value() -> None:
    entity = SystemMetadata(key="schema_version", value={"version": 1})
    previous = entity.updated_at
    entity.update_value({"version": 2})
    assert entity.value == {"version": 2}
    assert entity.updated_at >= previous
