"""Peak RSS sampling helpers for benchmark rows.

The phase-3 report needs a memory-scaling curve across fixture sizes, not just final
output sizes. Rows run in their own subprocess, so sampling this process' RSS while
conversion is in flight gives an apples-to-apples per-adapter peak memory signal.
"""

from __future__ import annotations

import asyncio
import resource
import sys
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


def ru_maxrss_bytes() -> int:
    """Return ``resource.ru_maxrss`` normalized to bytes on macOS/Linux."""

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return int(value)
    return int(value) * 1024


@dataclass(frozen=True)
class PeakRssResult:
    interval_s: float
    baseline_bytes: int
    final_bytes: int
    peak_bytes: int
    peak_delta_bytes: int
    samples: int
    sample_offsets_s: tuple[float, ...]
    sample_bytes: tuple[int, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "interval_s": self.interval_s,
            "baseline_bytes": self.baseline_bytes,
            "final_bytes": self.final_bytes,
            "peak_bytes": self.peak_bytes,
            "peak_delta_bytes": self.peak_delta_bytes,
            "samples": self.samples,
            "sample_offsets_s": list(self.sample_offsets_s),
            "sample_bytes": list(self.sample_bytes),
        }


async def sample_peak_rss_while(
    awaitable: Awaitable[T],
    *,
    read_rss_bytes: Callable[[], int] = ru_maxrss_bytes,
    interval_s: float = 0.02,
) -> tuple[T, PeakRssResult]:
    """Await ``awaitable`` while sampling RSS and return its result plus peak stats."""

    task = asyncio.create_task(awaitable)
    started = time.perf_counter()
    offsets: list[float] = [0.0]
    samples: list[int] = [read_rss_bytes()]
    try:
        while not task.done():
            await asyncio.sleep(interval_s)
            offsets.append(time.perf_counter() - started)
            samples.append(read_rss_bytes())
        value = await task
    finally:
        # Capture a final sample even when the workload raises; if it did raise the
        # exception is re-raised after this finally block by ``await task`` above.
        if not task.cancelled():
            offsets.append(time.perf_counter() - started)
            samples.append(read_rss_bytes())
    baseline = samples[0]
    final = samples[-1]
    peak = max(samples)
    return value, PeakRssResult(
        interval_s=interval_s,
        baseline_bytes=baseline,
        final_bytes=final,
        peak_bytes=peak,
        peak_delta_bytes=max(0, peak - baseline),
        samples=len(samples),
        sample_offsets_s=tuple(offsets),
        sample_bytes=tuple(samples),
    )
