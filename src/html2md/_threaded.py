"""``ChunkPump`` — drives the streaming conversion on a worker thread.

This is the configuration the GIL spikes measured as loop-alive: each input chunk's
feed+emit runs via ``asyncio.to_thread`` with the event loop awaited *between* chunks
(not one persistent never-yielding worker). The target parser releases the GIL at
element granularity within each ``feed()``, so the main loop's heartbeat stays
responsive throughout (design §4.2, §4.5).

Foundation behavior: the emitter produces the document at ``close()``, so the pump
delivers it once at the end. When the emit rules add safe-flush barriers (design §4.7),
the per-chunk loop drains committed Markdown into a bounded queue for true incremental
streaming with back-pressure; the drain point is marked below.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable, AsyncIterator

from .options import Options
from .parser import IncrementalDriver


class ChunkPump:
    """Feeds an async stream of HTML byte chunks through the driver on a worker thread."""

    __slots__ = ("options",)

    def __init__(self, options: Options | None = None) -> None:
        self.options = options or Options()

    async def run(self, chunks: AsyncIterable[bytes]) -> AsyncIterator[str]:
        driver = IncrementalDriver(self.options)
        try:
            async for chunk in chunks:
                data = chunk if isinstance(chunk, bytes) else bytes(chunk)
                # feed+emit one chunk off the loop; the loop runs between chunks.
                await asyncio.to_thread(driver.feed, data)
                # DRAIN POINT (design §4.7): once barriers commit output incrementally,
                # yield driver.drain() here for true streaming. No-op until then.
            result = await asyncio.to_thread(driver.close)
            if result:
                yield result
        finally:
            # Release the C parser even on cancellation/exception mid-stream. close()
            # is idempotent, so this is safe after a normal finish too.
            await asyncio.to_thread(driver.close)
