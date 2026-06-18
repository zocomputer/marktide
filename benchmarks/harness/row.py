"""Subprocess entry point for one phase-1 benchmark row."""

from __future__ import annotations

import argparse
import asyncio
import json
import resource
import sys
import time
from pathlib import Path
from typing import Any

from benchmarks.harness.adapters.base import get_adapters, supports_streaming
from benchmarks.harness.probe import Placement, probe_adapter, probe_streaming_adapter


def _ru_maxrss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return int(value)
    return int(value) * 1024


def _adapter_by_name(name: str):
    for adapter in get_adapters(include_lxml_naive=True):
        if adapter.name == name:
            return adapter
    known = ", ".join(adapter.name for adapter in get_adapters(include_lxml_naive=True))
    raise SystemExit(f"unknown adapter {name!r}; known: {known}")


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    adapter = _adapter_by_name(args.adapter)
    # Warm imports/native dispatch on a tiny payload so the measured fixture row is
    # closer to design.md's warm-throughput gate while still timing exactly one
    # full conversion for output hash/heartbeat metrics.
    adapter.convert(b"<p>warmup</p>")
    payload = Path(args.fixture).read_bytes()
    rss_before = _ru_maxrss_bytes()
    t0 = time.perf_counter()
    heartbeat = await probe_adapter(
        f"{adapter.name}:{args.fixture_name}",
        adapter.convert,
        payload,
        placement=Placement.TO_THREAD,
        interval_s=args.interval_s,
        duration_s=args.duration_s,
        repeat_until_duration=False,
    )
    wall_s = time.perf_counter() - t0
    rss_after = _ru_maxrss_bytes()
    conversion_wall_s = (
        heartbeat.conversion_wall_s
        if heartbeat.conversion_wall_s is not None
        else wall_s
    )
    input_bytes = len(payload)
    throughput_mib_s = (
        (input_bytes / 1024 / 1024) / conversion_wall_s
        if conversion_wall_s > 0
        else None
    )
    missed_beat_pct = (
        (heartbeat.missed_beats / heartbeat.samples * 100.0)
        if heartbeat.samples
        else None
    )
    streaming_cadence = None
    if supports_streaming(adapter):
        streaming_probe = await probe_streaming_adapter(
            f"{adapter.name}:{args.fixture_name}:streaming",
            adapter.convert_stream_chunks,
            payload,
        )
        streaming_cadence = streaming_probe.as_dict()

    return {
        "adapter": adapter.name,
        "package": adapter.package,
        "engine": adapter.engine,
        "fixture": args.fixture_name,
        "fixture_path": str(args.fixture),
        "input_bytes": input_bytes,
        "conversion_wall_s": conversion_wall_s,
        "subprocess_wall_s": wall_s,
        "throughput_mib_s": throughput_mib_s,
        "ru_maxrss_before_bytes": rss_before,
        "ru_maxrss_after_bytes": rss_after,
        "ru_maxrss_delta_bytes": max(0, rss_after - rss_before),
        "output_bytes": heartbeat.output_bytes,
        "output_hash": heartbeat.output_hash,
        "output_to_input_ratio": (heartbeat.output_bytes / input_bytes)
        if heartbeat.output_bytes is not None
        else None,
        "heartbeat": heartbeat.as_dict(),
        "streaming_cadence": streaming_cadence,
        "async_gate": {
            "missed_beat_pct": missed_beat_pct,
            "max_delay_ms": heartbeat.max_ms,
            "p99_delay_ms": heartbeat.p99_ms,
            "passes_v1_worker_async": (
                missed_beat_pct is not None
                and missed_beat_pct < 2.0
                and heartbeat.max_ms < 15.0
            ),
        },
        "option_map": {
            "settings": adapter.option_map.settings,
            "targets": adapter.option_map.targets,
            "residual": list(adapter.option_map.residual),
        },
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--fixture-name", required=True)
    parser.add_argument("--interval-s", type=float, default=0.005)
    parser.add_argument("--duration-s", type=float, default=1.0)
    args = parser.parse_args(argv)
    result = asyncio.run(_run(args))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
