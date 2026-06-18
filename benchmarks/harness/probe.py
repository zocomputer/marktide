"""Async heartbeat / GIL-release probe for benchmark adapters."""

from __future__ import annotations

import asyncio
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

DEFAULT_INTERVAL_S = 0.001
DEFAULT_DURATION_S = 1.0


class Placement(StrEnum):
    INLINE = "inline"
    TO_THREAD = "to_thread"


@dataclass(frozen=True)
class HeartbeatResult:
    workload: str
    placement: Placement
    interval_s: float
    samples: int
    conversion_wall_s: float | None
    per_iter_s: float | None
    iterations: int | None
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    total_stall_ms: float
    missed_beats: int
    longest_contiguous_stall_ms: float
    output_bytes: int | None = None
    output_hash: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "workload": self.workload,
            "placement": self.placement.value,
            "interval_s": self.interval_s,
            "samples": self.samples,
            "conversion_wall_s": self.conversion_wall_s,
            "per_iter_s": self.per_iter_s,
            "iterations": self.iterations,
            "mean_ms": self.mean_ms,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "max_ms": self.max_ms,
            "total_stall_ms": self.total_stall_ms,
            "missed_beats": self.missed_beats,
            "longest_contiguous_stall_ms": self.longest_contiguous_stall_ms,
            "output_bytes": self.output_bytes,
            "output_hash": self.output_hash,
        }


def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return float("nan")
    return sorted_values[min(len(sorted_values) - 1, int(q * len(sorted_values)))]


def _summarize(
    workload: str,
    placement: Placement,
    interval_s: float,
    jitter_ms: list[float],
    conversion_wall_s: float | None,
    per_iter_s: float | None,
    iterations: int | None,
    output: str | None = None,
) -> HeartbeatResult:
    import hashlib

    sorted_jitter = sorted(jitter_ms)
    miss_threshold_ms = interval_s * 2000.0
    stalls = [max(0.0, value) for value in jitter_ms]
    longest = max(stalls) if stalls else float("nan")
    output_bytes: int | None = None
    output_hash: str | None = None
    if output is not None:
        encoded = output.encode("utf-8", errors="replace")
        output_bytes = len(encoded)
        output_hash = hashlib.sha256(encoded).hexdigest()
    return HeartbeatResult(
        workload=workload,
        placement=placement,
        interval_s=interval_s,
        samples=len(jitter_ms),
        conversion_wall_s=conversion_wall_s,
        per_iter_s=per_iter_s,
        iterations=iterations,
        mean_ms=statistics.mean(jitter_ms) if jitter_ms else float("nan"),
        p50_ms=_percentile(sorted_jitter, 0.50),
        p95_ms=_percentile(sorted_jitter, 0.95),
        p99_ms=_percentile(sorted_jitter, 0.99),
        max_ms=max(jitter_ms) if jitter_ms else float("nan"),
        total_stall_ms=sum(stalls),
        missed_beats=sum(1 for value in jitter_ms if value > miss_threshold_ms),
        longest_contiguous_stall_ms=longest,
        output_bytes=output_bytes,
        output_hash=output_hash,
    )


async def probe_adapter(
    name: str,
    convert: Callable[[bytes], str],
    payload: bytes,
    *,
    placement: Placement = Placement.TO_THREAD,
    interval_s: float = DEFAULT_INTERVAL_S,
    duration_s: float = DEFAULT_DURATION_S,
    repeat_until_duration: bool = False,
) -> HeartbeatResult:
    """Measure event-loop heartbeat jitter while ``convert(payload)`` runs.

    The default is **single-conversion mode**: run exactly one conversion and
    sample the heartbeat from start until that conversion completes. This is the
    mode for real adapter×fixture benchmark rows, because output hash/bytes and
    heartbeat metrics describe the same exact conversion.

    ``repeat_until_duration=True`` is reserved for calibration controls that are
    too short to produce enough heartbeat samples in one call.
    """

    if placement == Placement.TO_THREAD:
        return await _probe_to_thread(
            name,
            convert,
            payload,
            interval_s=interval_s,
            duration_s=duration_s,
            repeat_until_duration=repeat_until_duration,
        )
    if placement == Placement.INLINE:
        return await _probe_inline(
            name,
            convert,
            payload,
            interval_s=interval_s,
            duration_s=duration_s,
            repeat_until_duration=repeat_until_duration,
        )
    raise ValueError(f"unknown placement: {placement}")


async def _probe_to_thread(
    name: str,
    convert: Callable[[bytes], str],
    payload: bytes,
    *,
    interval_s: float,
    duration_s: float,
    repeat_until_duration: bool,
) -> HeartbeatResult:
    done = asyncio.Event()
    timing: dict[str, Any] = {}

    async def worker() -> None:
        t0 = time.perf_counter()
        iterations = 0
        last_output = ""
        try:
            if repeat_until_duration:
                while time.perf_counter() - t0 < duration_s:
                    last_output = await asyncio.to_thread(convert, payload)
                    iterations += 1
            else:
                last_output = await asyncio.to_thread(convert, payload)
                iterations = 1
        except BaseException as exc:  # propagate after heartbeat sampling exits
            timing["exception"] = exc
        finally:
            elapsed = time.perf_counter() - t0
            timing["conversion_wall_s"] = elapsed
            timing["per_iter_s"] = elapsed / max(iterations, 1) if iterations else None
            timing["iterations"] = iterations
            timing["output"] = last_output
            done.set()

    worker_task = asyncio.create_task(worker())
    jitter_ms: list[float] = []
    while not done.is_set():
        t0 = time.perf_counter()
        await asyncio.sleep(interval_s)
        jitter_ms.append((time.perf_counter() - t0 - interval_s) * 1000.0)
    await worker_task
    if "exception" in timing:
        raise timing["exception"]
    return _summarize(
        name,
        Placement.TO_THREAD,
        interval_s,
        jitter_ms,
        timing.get("conversion_wall_s"),
        timing.get("per_iter_s"),
        timing.get("iterations"),
        timing.get("output"),
    )


async def _probe_inline(
    name: str,
    convert: Callable[[bytes], str],
    payload: bytes,
    *,
    interval_s: float,
    duration_s: float,
    repeat_until_duration: bool,
) -> HeartbeatResult:
    jitter_ms: list[float] = []
    per_iter: list[float] = []
    output = ""
    start = time.perf_counter()
    iterations = 0
    while True:
        for _ in range(3 if repeat_until_duration else 1):
            t0 = time.perf_counter()
            await asyncio.sleep(interval_s)
            jitter_ms.append((time.perf_counter() - t0 - interval_s) * 1000.0)
        t0 = time.perf_counter()
        await asyncio.sleep(interval_s)
        work_start = time.perf_counter()
        output = convert(payload)
        per_iter.append(time.perf_counter() - work_start)
        iterations += 1
        jitter_ms.append((time.perf_counter() - t0 - interval_s) * 1000.0)
        if not repeat_until_duration or time.perf_counter() - start >= duration_s:
            break
    elapsed = time.perf_counter() - start
    return _summarize(
        name,
        Placement.INLINE,
        interval_s,
        jitter_ms,
        elapsed,
        statistics.mean(per_iter) if per_iter else None,
        iterations,
        output,
    )


# Probe controls -------------------------------------------------------------

def pure_python_burn(payload: bytes | None = None) -> str:
    n = 0
    for _ in range(2_000_000):
        n += 1
    return str(n)


def gil_releasing_sleep(payload: bytes | None = None) -> str:
    time.sleep(0.05)
    return "sleep"


def mixed_cpu_sleep(payload: bytes | None = None) -> str:
    n = 0
    for _ in range(4):
        for _ in range(250_000):
            n += 1
        time.sleep(0.01)
    return str(n)
