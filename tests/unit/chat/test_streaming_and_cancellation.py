"""Unit tests for streaming heartbeat interleaving and cancellation registry."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from contextforge.modules.chat.application.services.streaming import iterate_with_heartbeat
from contextforge.modules.chat.infrastructure.cancellation import (
    InMemoryStreamCancellationRegistry,
)


async def _fast_source(items: list[str]) -> AsyncIterator[str]:
    for item in items:
        yield item


async def _slow_source(items: list[str], *, delay: float) -> AsyncIterator[str]:
    for item in items:
        await asyncio.sleep(delay)
        yield item


async def _failing_source() -> AsyncIterator[str]:
    yield "partial"
    msg = "upstream failure"
    raise RuntimeError(msg)
    yield "unreachable"  # pragma: no cover


@pytest.mark.unit
class TestIterateWithHeartbeat:
    async def test_yields_all_tokens_without_heartbeats(self) -> None:
        results = [
            item
            async for item in iterate_with_heartbeat(_fast_source(["a", "b", "c"]), interval=1.0)
        ]
        assert results == [("token", "a"), ("token", "b"), ("token", "c")]

    async def test_emits_heartbeat_during_idle_period(self) -> None:
        results = [
            item
            async for item in iterate_with_heartbeat(
                _slow_source(["a", "b"], delay=0.05), interval=0.01
            )
        ]
        kinds = [kind for kind, _ in results]
        assert "heartbeat" in kinds
        assert ("token", "a") in results
        assert ("token", "b") in results

    async def test_propagates_upstream_error(self) -> None:
        results = [item async for item in iterate_with_heartbeat(_failing_source(), interval=1.0)]
        assert results[0] == ("token", "partial")
        assert results[-1][0] == "error"
        assert "upstream failure" in results[-1][1]


@pytest.mark.unit
class TestInMemoryStreamCancellationRegistry:
    def test_new_message_is_not_cancelled(self) -> None:
        registry = InMemoryStreamCancellationRegistry()
        message_id = uuid4()
        registry.begin(message_id)
        assert registry.is_cancelled(message_id) is False

    def test_cancel_marks_active_message(self) -> None:
        registry = InMemoryStreamCancellationRegistry()
        message_id = uuid4()
        registry.begin(message_id)
        assert registry.cancel(message_id) is True
        assert registry.is_cancelled(message_id) is True

    def test_cancel_unknown_message_returns_false(self) -> None:
        registry = InMemoryStreamCancellationRegistry()
        assert registry.cancel(uuid4()) is False

    def test_end_clears_state(self) -> None:
        registry = InMemoryStreamCancellationRegistry()
        message_id = uuid4()
        registry.begin(message_id)
        registry.cancel(message_id)
        registry.end(message_id)
        assert registry.is_cancelled(message_id) is False
        assert registry.cancel(message_id) is False
