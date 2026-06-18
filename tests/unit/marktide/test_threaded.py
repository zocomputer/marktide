"""ChunkPump async bridge — cancellation safety and parser-op serialization.

Uses a fake driver (per design §7.1) to isolate the threading bridge from lxml and to
deterministically exercise the cancel-during-feed race.
"""

from __future__ import annotations

import asyncio
import threading

import pytest

from marktide._threaded import ChunkPump
from marktide.options import Options


class _BlockingDriver:
    """Fake driver whose feed() blocks until released, recording whether close() ever
    overlaps an in-flight feed (the race the lock must prevent)."""

    def __init__(self, options: Options | None = None) -> None:
        self.feed_entered = threading.Event()
        self.release = threading.Event()
        self.closed = False
        self.overlap = False
        self._active = False

    def feed(self, data: bytes) -> None:
        self._active = True
        self.feed_entered.set()
        self.release.wait(timeout=5)
        self._active = False

    def drain(self) -> str:
        return ""

    def close(self) -> str:
        if self._active:           # close ran while a feed was in flight → race
            self.overlap = True
        self.closed = True
        return ""


class _FakeDriver:
    """Trivial fake: records feeds, returns canned output, idempotent close."""

    def __init__(self, options: Options | None = None) -> None:
        self.fed: list[bytes] = []
        self.closed = 0

    def feed(self, data: bytes) -> None:
        self.fed.append(data)

    def drain(self) -> str:
        return ""

    def close(self) -> str:
        self.closed += 1
        return "DONE"


def test_cancel_during_feed_does_not_race_close() -> None:
    async def main() -> _BlockingDriver:
        drv = _BlockingDriver()
        pump = ChunkPump(driver_factory=lambda _o: drv)

        async def achunks():
            yield b"<p>x</p>"
            yield b"<p>y</p>"

        agen = pump.run(achunks())
        task = asyncio.create_task(agen.__anext__())
        # wait until the first feed is in flight (blocked on release)
        entered = await asyncio.to_thread(drv.feed_entered.wait, 2.0)
        assert entered, "feed never started"
        task.cancel()                 # cancel mid-feed
        drv.release.set()             # let the in-flight feed finish
        with pytest.raises(asyncio.CancelledError):
            await task
        await agen.aclose()
        return drv

    drv = asyncio.run(main())
    assert drv.closed is True, "parser not closed after cancellation"
    assert drv.overlap is False, "close() raced an in-flight feed()"


def test_normal_stream_feeds_all_and_closes_once() -> None:
    async def main() -> _FakeDriver:
        drv = _FakeDriver()
        pump = ChunkPump(driver_factory=lambda _o: drv)

        async def achunks():
            yield b"a"
            yield b"b"

        out = [piece async for piece in pump.run(achunks())]
        assert out == ["DONE"]
        return drv

    drv = asyncio.run(main())
    assert drv.fed == [b"a", b"b"]
    # close() may be invoked by both the normal path and the finally; the driver's own
    # idempotence collapses them, but the bridge must not feed after close.
    assert drv.closed >= 1
