"""``ChunkPump`` — drives the streaming conversion on a worker thread.

This is the configuration the GIL spikes measured as loop-alive: each input chunk's
feed+emit runs via ``asyncio.to_thread`` with the event loop awaited *between* chunks
(not one persistent never-yielding worker). The target parser releases the GIL at
element granularity within each ``feed()``, so the main loop's heartbeat stays
responsive throughout (design §4.2, §4.5). After each feed the pump drains the output
that is safe to emit and yields it, so consumers see Markdown before EOF (§4.7); the
async generator's natural back-pressure paces the producer.

Thread-safety: lxml's parser is **not** thread-safe, and ``asyncio.to_thread`` cannot
cancel a thread already running ``feed``. If the stream is cancelled mid-``feed`` and
cleanup called ``close`` on another worker thread, the two would touch the parser
concurrently. All parser operations are therefore serialized through a single lock, so
``close`` blocks until any in-flight ``feed`` finishes — they never overlap — and the
final ``close`` is run to completion even while the coroutine is being cancelled.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterable, AsyncIterator, Callable, Coroutine
from typing import Any

from .options import Options
from .parser import IncrementalDriver


class ChunkPump:
    """Feeds an async stream of HTML byte chunks through the driver on a worker thread."""

    __slots__ = ("options", "_make_driver")

    def __init__(
        self,
        options: Options | None = None,
        *,
        driver_factory: Callable[[Options], IncrementalDriver] = IncrementalDriver,
    ) -> None:
        self.options = options or Options()
        # injectable for tests (fake driver isolates the bridge from lxml).
        self._make_driver = driver_factory

    async def run(self, chunks: AsyncIterable[bytes]) -> AsyncIterator[str]:
        driver = self._make_driver(self.options)
        lock = threading.Lock()  # serialize all parser ops — lxml is not thread-safe

        def feed(data: bytes) -> None:
            with lock:
                driver.feed(data)

        def drain() -> str:
            with lock:
                return driver.drain()

        def close() -> str:
            with lock:  # blocks until any in-flight feed() releases the parser
                return driver.close()

        try:
            async for chunk in chunks:
                data = chunk if isinstance(chunk, bytes) else bytes(chunk)
                await asyncio.to_thread(feed, data)
                piece = await asyncio.to_thread(drain)
                if piece:
                    yield piece
            result = await asyncio.to_thread(close)
            if result:
                yield result
        finally:
            await _run_to_completion(asyncio.to_thread(close))


async def _run_to_completion(coro: Coroutine[Any, Any, str]) -> None:
    """Await ``coro`` (the final close) to completion even if the surrounding coroutine
    is being cancelled, so the C parser is always released. The serialization lock makes
    this close wait for any in-flight feed rather than racing it."""
    task = asyncio.ensure_future(coro)
    while True:
        try:
            await asyncio.shield(task)
            return
        except asyncio.CancelledError:
            # We were cancelled while awaiting the shielded close. Let it finish (it is
            # already running and serialized behind any in-flight feed), then re-raise.
            await asyncio.gather(task, return_exceptions=True)
            raise
