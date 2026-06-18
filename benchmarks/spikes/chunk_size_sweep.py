"""SPIKE (bead zo-1fp.6) — lxml target-parser feed() chunk-size sweep.

Runs lxml.etree.HTMLParser(target=...) on a worker thread, feeding the same HTML
bytes in configurable chunks while the main thread records asyncio heartbeat
jitter. The target callback intentionally does tiny Python bookkeeping for each
start/end/data callback so the measurement captures the callback-heavy parser
mode the streaming converter would use.

Usage:
    uv run python benchmarks/spikes/chunk_size_sweep.py [html_path]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import threading
import time
from pathlib import Path
from typing import Any

INTERVAL_S = 0.001
CHUNK_SIZES = [4 * 1024, 16 * 1024, 64 * 1024, 256 * 1024, 1024 * 1024]


class CountingTarget:
    def __init__(self) -> None:
        self.starts = 0
        self.ends = 0
        self.data_events = 0
        self.text_chars = 0

    def start(self, tag: str, attrib: dict[str, str]) -> None:
        self.starts += 1

    def end(self, tag: str) -> None:
        self.ends += 1

    def data(self, data: str) -> None:
        self.data_events += 1
        self.text_chars += len(data)

    def comment(self, text: str) -> None:
        pass

    def close(self) -> dict[str, int]:
        return {
            "starts": self.starts,
            "ends": self.ends,
            "data_events": self.data_events,
            "text_chars": self.text_chars,
        }


def pct(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def summarize_jitter(jitter_ms: list[float]) -> dict[str, float | int]:
    return {
        "samples": len(jitter_ms),
        "mean_ms": statistics.mean(jitter_ms) if jitter_ms else float("nan"),
        "p50_ms": pct(jitter_ms, 0.50),
        "p95_ms": pct(jitter_ms, 0.95),
        "p99_ms": pct(jitter_ms, 0.99),
        "max_ms": max(jitter_ms) if jitter_ms else float("nan"),
    }


def feed_parse(html_bytes: bytes, chunk_size: int) -> dict[str, Any]:
    from lxml import etree

    target = CountingTarget()
    parser = etree.HTMLParser(target=target, huge_tree=True, recover=True)
    started = time.perf_counter()
    for offset in range(0, len(html_bytes), chunk_size):
        parser.feed(html_bytes[offset : offset + chunk_size])
    counts = parser.close()
    elapsed = time.perf_counter() - started
    return {
        "parse_s": elapsed,
        "throughput_mib_s": (len(html_bytes) / 1024 / 1024) / elapsed,
        "chunks": (len(html_bytes) + chunk_size - 1) // chunk_size,
        "target_counts": counts,
    }


async def measure_worker(fn, *args) -> tuple[dict[str, Any], dict[str, float | int]]:
    done = threading.Event()
    holder: dict[str, Any] = {}

    def runner() -> None:
        try:
            holder["result"] = fn(*args)
        except BaseException as exc:  # noqa: BLE001 - propagate from worker
            holder["error"] = exc
        finally:
            done.set()

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    jitter_ms: list[float] = []
    while not done.is_set():
        t0 = time.perf_counter()
        await asyncio.sleep(INTERVAL_S)
        jitter_ms.append((time.perf_counter() - t0 - INTERVAL_S) * 1000.0)
    thread.join()
    if "error" in holder:
        raise holder["error"]
    return holder["result"], summarize_jitter(jitter_ms)


async def measure_idle(duration_s: float) -> dict[str, float | int]:
    end_at = time.perf_counter() + duration_s
    jitter_ms: list[float] = []
    while time.perf_counter() < end_at:
        t0 = time.perf_counter()
        await asyncio.sleep(INTERVAL_S)
        jitter_ms.append((time.perf_counter() - t0 - INTERVAL_S) * 1000.0)
    return summarize_jitter(jitter_ms)


async def run(path: Path) -> dict[str, Any]:
    html_bytes = path.read_bytes()
    rows = []
    # Warm import/cache outside measured rows.
    feed_parse(html_bytes[: min(len(html_bytes), 1024 * 1024)], 64 * 1024)
    idle = await measure_idle(0.75)
    for chunk_size in CHUNK_SIZES:
        worker, jitter = await measure_worker(feed_parse, html_bytes, chunk_size)
        rows.append({
            "chunk_size_bytes": chunk_size,
            "chunk_size_kib": chunk_size // 1024,
            **worker,
            **jitter,
        })
    return {
        "python": sys.version.split()[0],
        "heartbeat_interval_ms": INTERVAL_S * 1000,
        "input_path": str(path),
        "input_bytes": len(html_bytes),
        "input_mib": len(html_bytes) / 1024 / 1024,
        "idle_jitter": idle,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "html_path",
        nargs="?",
        default="benchmarks/spikes/sample_50mb.html",
        help="HTML input path; default uses coder-3's generated 50MiB spike sample",
    )
    args = parser.parse_args()
    result = asyncio.run(run(Path(args.html_path)))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
