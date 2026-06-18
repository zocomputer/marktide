"""Orchestration — ties the driver + emitter + options into the public conversions.

Sync entry points drive the feed loop to completion and return/yield Markdown. Async
entry points run the (GIL-holding) emit work on a worker thread; the event loop stays
responsive because the target parser releases the GIL at element granularity within
``feed()`` and the worker yields between chunks (design §4.2, validated by the GIL
spikes). The streaming variants are backed by :class:`~marktide._threaded.ChunkPump`.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable, AsyncIterator, Iterable, Iterator

from .options import Options
from .parser import IncrementalDriver


def _to_bytes(html: str | bytes) -> bytes:
    # bytes are fed straight to lxml (it sniffs the declared encoding); str is encoded
    # to UTF-8 first (design §6.1).
    return html if isinstance(html, bytes) else html.encode("utf-8")


def convert(html: str | bytes, *, options: Options | None = None) -> str:
    """Convert a whole HTML document to Markdown (one-shot, sync)."""
    options = options or Options()
    data = _to_bytes(html)
    with IncrementalDriver(options) as driver:
        driver.feed_all(data)
        return driver.close()


async def convert_async(html: str | bytes, *, options: Options | None = None) -> str:
    """Convert a whole HTML document to Markdown off the event loop."""
    return await asyncio.to_thread(convert, html, options=options)


def convert_stream(
    chunks: Iterable[bytes], *, options: Options | None = None
) -> Iterator[str]:
    """Convert a stream of HTML byte chunks to a stream of Markdown chunks (sync).

    Yields Markdown incrementally: after each fed input chunk, any output that is safe
    to emit (completed top-level blocks, trailing whitespace held back per the §4.7
    barrier) is drained and yielded; the final remainder is flushed at close. The
    concatenation of all yielded chunks is exactly ``convert(...)``.
    """
    options = options or Options()
    with IncrementalDriver(options) as driver:
        for chunk in chunks:
            driver.feed(chunk if isinstance(chunk, bytes) else _to_bytes(chunk))
            piece = driver.drain()
            if piece:
                yield piece
        result = driver.close()
    if result:
        yield result


async def convert_stream_async(
    chunks: AsyncIterable[bytes], *, options: Options | None = None
) -> AsyncIterator[str]:
    """Convert an async stream of HTML byte chunks to an async stream of Markdown.

    Backed by :class:`~marktide._threaded.ChunkPump`: each input chunk's feed+emit runs
    on a worker thread with the event loop awaited between chunks (the loop-alive
    configuration validated by the GIL spikes), and Markdown is delivered over a bounded
    queue for back-pressure. Foundation behavior matches ``convert_stream`` (final
    document delivered once); incremental flush arrives with the emit rules.
    """
    from ._threaded import ChunkPump

    options = options or Options()
    pump = ChunkPump(options)
    async for markdown in pump.run(chunks):
        yield markdown
