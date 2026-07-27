from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator


async def iterate_with_heartbeat(
    source: AsyncIterator[str], *, interval: float
) -> AsyncIterator[tuple[str, str]]:
    queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

    async def _pump() -> None:
        try:
            async for delta in source:
                await queue.put(("token", delta))
        except Exception as exc:
            await queue.put(("error", str(exc)))
        finally:
            await queue.put(None)

    task = asyncio.create_task(_pump())
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=interval)
            except TimeoutError:
                yield ("heartbeat", "")
                continue
            if item is None:
                break
            yield item
            if item[0] == "error":
                break
    finally:
        if not task.done():
            task.cancel()
        with contextlib.suppress(BaseException):
            await task


__all__ = ["iterate_with_heartbeat"]
