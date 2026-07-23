"""Shared async retry helper."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


async def retry_async[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    backoff_seconds: float,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """Retry ``operation`` with exponential backoff for selected exceptions."""
    attempt = 0
    while True:
        try:
            return await operation()
        except retry_on:
            if attempt >= max_retries:
                raise
            delay = backoff_seconds * (2**attempt)
            await asyncio.sleep(delay)
            attempt += 1


__all__ = ["retry_async"]
