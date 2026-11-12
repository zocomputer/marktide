"""Keep native parser finalization alive through repeated request cancellation."""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from marktide._threaded import ChunkPump, _run_to_completion
from marktide.options import Options
from marktide.parser import IncrementalDriver


def test_repeated_cancellation_does_not_discard_queued_native_close() -> None:
    async def main() -> tuple[bool, bool, bool]:
        loop = asyncio.get_running_loop()
        feed_entered = asyncio.Event()
        close_queued = asyncio.Event()
        release_feed = threading.Event()

        # --- Deterministic scheduling helpers ---
        class Executor(ThreadPoolExecutor):
            def __init__(self) -> None:
                super().__init__(max_workers=1)
                self.submissions = 0

            def submit(self, fn, /, *args, **kwargs):
                future = super().submit(fn, *args, **kwargs)
                self.submissions += 1
                if self.submissions == 2:
                    close_queued.set()
                return future

        class Driver(IncrementalDriver):
            def __init__(self) -> None:
                super().__init__(Options())
                self.close_completed = False
                self.feed_active = False
                self.overlap = False

            def feed(self, data: bytes) -> None:
                self.feed_active = True
                try:
                    super().feed(data)
                    loop.call_soon_threadsafe(feed_entered.set)
                    if not release_feed.wait(timeout=5):
                        raise TimeoutError("test did not release native feed")
                finally:
                    self.feed_active = False

            def close(self) -> str:
                self.overlap |= self.feed_active
                result = super().close()
                self.close_completed = True
                return result

        async def chunks():
            yield b"<p>cancelled conversion</p>"
        # --- End deterministic scheduling helpers ---

        executor = Executor()
        loop.set_default_executor(executor)
        driver = Driver()
        stream = ChunkPump(driver_factory=lambda _options: driver).run(chunks())
        consumer = asyncio.create_task(stream.__anext__())
        try:
            await asyncio.wait_for(feed_entered.wait(), timeout=2)
            consumer.cancel()
            await asyncio.wait_for(close_queued.wait(), timeout=2)
            # Deliver each cancellation in a separate loop turn while close is
            # queued behind the occupied worker. No timing sleeps are needed.
            for _ in range(4):
                consumer.cancel()
                await asyncio.sleep(0)
            returned_before_cleanup = consumer.done()
        finally:
            release_feed.set()
            with pytest.raises(asyncio.CancelledError):
                await consumer
            await stream.aclose()
            await loop.shutdown_default_executor()

        return returned_before_cleanup, driver.close_completed, driver.overlap

    returned_early, closed, overlap = asyncio.run(main())
    assert (returned_early, closed, overlap) == (False, True, False), (
        "cancelled requests must wait for native close without overlapping feed; "
        f"returned_early={returned_early}, closed={closed}, overlap={overlap}"
    )


@pytest.mark.parametrize("cancel_count", [0, 3])
@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_cleanup_preserves_error_and_cancellation_precedence(
    cancel_count: int, cleanup_fails: bool
) -> None:
    async def main() -> None:
        started = asyncio.Event()
        release = asyncio.Event()
        completed = False

        async def cleanup() -> str:
            nonlocal completed
            started.set()
            await release.wait()
            completed = True
            if cleanup_fails:
                raise ValueError("cleanup failed")
            return "done"

        task = asyncio.create_task(_run_to_completion(cleanup()))
        try:
            await asyncio.wait_for(started.wait(), timeout=2)
            for _ in range(cancel_count):
                task.cancel("request cancelled")
                await asyncio.sleep(0)
        finally:
            release.set()
        if cancel_count:
            with pytest.raises(asyncio.CancelledError, match="request cancelled"):
                await task
        elif cleanup_fails:
            with pytest.raises(ValueError, match="cleanup failed"):
                await task
        else:
            await task
        assert completed, "cancellation discarded the cleanup coroutine"

    asyncio.run(main())


def test_cleanup_self_cancellation_terminates() -> None:
    async def main() -> None:
        async def cleanup() -> str:
            raise asyncio.CancelledError("cleanup cancelled itself")

        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(_run_to_completion(cleanup()), timeout=2)

    asyncio.run(main())
