"""Phase-1 benchmark matrix runner.

This runner intentionally produces the final phase-1 artifacts only; it does not
implement the phase-3 html2md comparison runner yet.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.harness.adapters.base import get_adapters
from benchmarks.harness.fixtures import FIXTURE_ORDER, load_fixture_set

RESULTS_DIR = Path("benchmarks/results")
PHASE1_JSON = RESULTS_DIR / "phase1.json"
PHASE1_REPORT = RESULTS_DIR / "report.md"
DEFAULT_ADAPTERS = (
    "markdownify",
    "html_to_markdown",
    "htmd_py",
    "html2text_rs",
    "html2md",
    "html2md_streaming",
    "lxml_naive",
)
GATE_VERSION = "v1"


@dataclass(frozen=True)
class RowRequest:
    adapter: str
    fixture_name: str
    fixture_path: Path


def _known_adapter_names() -> set[str]:
    return {adapter.name for adapter in get_adapters(include_lxml_naive=True)}


def _run_row(
    request: RowRequest, *, interval_s: float, timeout_s: float
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "benchmarks.harness.row",
        "--adapter",
        request.adapter,
        "--fixture",
        str(request.fixture_path),
        "--fixture-name",
        request.fixture_name,
        "--interval-s",
        str(interval_s),
    ]
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd, check=False, capture_output=True, text=True, timeout=timeout_s
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "adapter": request.adapter,
            "fixture": request.fixture_name,
            "fixture_path": str(request.fixture_path),
            "status": "timeout",
            "timeout_s": timeout_s,
            "subprocess_wall_s": time.perf_counter() - started,
            "stdout": exc.stdout,
            "stderr": exc.stderr,
        }
    if proc.returncode != 0:
        return {
            "adapter": request.adapter,
            "fixture": request.fixture_name,
            "fixture_path": str(request.fixture_path),
            "status": "error",
            "returncode": proc.returncode,
            "subprocess_wall_s": time.perf_counter() - started,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    try:
        row = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {
            "adapter": request.adapter,
            "fixture": request.fixture_name,
            "fixture_path": str(request.fixture_path),
            "status": "bad-json",
            "subprocess_wall_s": time.perf_counter() - started,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "error": str(exc),
        }
    row["status"] = "ok"
    return row


def _evaluate_gate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_adapter: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        if row.get("status") != "ok":
            continue
        by_adapter.setdefault(row["adapter"], {})[row["fixture"]] = row

    markdownify = by_adapter.get("markdownify", {})
    evaluations: dict[str, Any] = {}
    for adapter, fixture_rows in by_adapter.items():
        if adapter == "markdownify":
            continue
        medium = fixture_rows.get("medium")
        large = fixture_rows.get("large")
        xlarge = fixture_rows.get("xlarge")
        md_medium = markdownify.get("medium")
        throughput_pass = False
        if (
            medium
            and md_medium
            and medium.get("throughput_mib_s")
            and md_medium.get("throughput_mib_s")
        ):
            rel = medium["throughput_mib_s"] / md_medium["throughput_mib_s"]
            abs_large = bool(
                large
                and large.get("throughput_mib_s")
                and large["throughput_mib_s"] >= 20.0
            )
            abs_xlarge = bool(
                xlarge
                and xlarge.get("throughput_mib_s")
                and xlarge["throughput_mib_s"] >= 20.0
            )
            throughput_pass = rel >= 5.0 and abs_large and abs_xlarge
        async_rows = [r for r in fixture_rows.values() if r.get("async_gate")]
        async_pass = bool(async_rows) and all(
            r["async_gate"].get("passes_v1_worker_async") for r in async_rows
        )
        one_shot_rss_pass = all(
            (r.get("ru_maxrss_delta_bytes") or 0) <= 3 * (r.get("input_bytes") or 1)
            for r in fixture_rows.values()
        )

        def _stream_row_pass(row: dict[str, Any] | None) -> bool:
            cadence = row.get("streaming_cadence") if row else None
            if not cadence:
                return False
            first_chunk_s = cadence.get("first_chunk_s")
            max_gap_s = cadence.get("max_inter_chunk_gap_s")
            return (
                first_chunk_s is not None
                and first_chunk_s <= 0.050
                and (max_gap_s is None or max_gap_s <= 0.100)
            )

        streaming_ttfo_pass = _stream_row_pass(large) and _stream_row_pass(xlarge)
        fidelity_pass = adapter in {
            "html_to_markdown",
            "htmd_py",
            "html2md",
            "html2md_streaming",
        }  # preliminary; conformance harness owns exact score.
        passes_all = (
            throughput_pass
            and async_pass
            and one_shot_rss_pass
            and streaming_ttfo_pass
            and fidelity_pass
        )
        evaluations[adapter] = {
            "throughput_pass": throughput_pass,
            "async_pass": async_pass,
            "rss_one_shot_pass": one_shot_rss_pass,
            "streaming_ttfo_pass": streaming_ttfo_pass,
            "fidelity_options_prelim_pass": fidelity_pass,
            "passes_all_v1": passes_all,
        }
    return {
        "gate_version": GATE_VERSION,
        "thresholds": {
            "throughput": "warm throughput >=5x markdownify on medium+ and >=20 MiB/s on large/xlarge",
            "async": "missed_beat_pct <2% and max_delay_ms <15ms on every tier",
            "rss": "one-shot path <=3x input bytes; streaming candidate <=256MiB constant on xlarge",
            "ttfo": "streaming only: first chunk <=50ms and max inter-chunk gap <=100ms on large/xlarge",
            "fidelity": ">=99% conformance vs markdownify oracle post-normalization",
        },
        "adapter_evaluations": evaluations,
        "phase2_required": not any(
            item["passes_all_v1"] for item in evaluations.values()
        ),
        "notes": [
            "TTFO criterion is measured only for adapters exposing streaming_cadence; one-shot-only libraries structurally fail it.",
            "Fidelity is preliminary here; tests/conformance differential harness owns exact conformance scoring.",
        ],
    }


def _format_float(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def _write_report(result: dict[str, Any], path: Path) -> None:
    rows = result["rows"]
    lines: list[str] = []
    lines.append("# Phase 1 HTML→Markdown benchmark report")
    lines.append("")
    lines.append(f"Generated: `{result['generated_at']}`")
    lines.append(f"Gate: `{result['gate']['gate_version']}`")
    lines.append(
        f"Fixture manifest: `{result['fixture_manifest']}` (canonical; no separate `manifest.json` is used)"
    )
    lines.append("")
    verdict = "BUILD phase 2" if result["gate"]["phase2_required"] else "SKIP phase 2"
    lines.append(f"## Verdict: {verdict}")
    lines.append("")
    lines.append(
        "Throughput is a warm single-conversion measurement after a tiny adapter warmup; output hash/bytes and heartbeat metrics describe that exact conversion. Native streaming adapters additionally report TTFO and inter-chunk cadence from their streaming API."
    )
    lines.append("")
    lines.append("## Matrix results")
    lines.append("")
    lines.append(
        "| Adapter | Fixture | Status | MiB/s | Wall s | Missed beat % | Max delay ms | p99 delay ms | TTFO ms | Max stream gap ms | Stream chunks | Output/Input | RSS delta MiB | Async pass |"
    )
    lines.append("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in rows:
        if row.get("status") != "ok":
            lines.append(
                f"| {row.get('adapter')} | {row.get('fixture')} | {row.get('status')} | — | — | — | — | — | — | — | — | — | — | no |"
            )
            continue
        async_gate = row["async_gate"]
        cadence = row.get("streaming_cadence") or {}
        lines.append(
            "| {adapter} | {fixture} | ok | {mibs} | {wall} | {missed} | {maxd} | {p99} | {ttfo} | {gap} | {chunks} | {ratio} | {rss} | {apass} |".format(
                adapter=row["adapter"],
                fixture=row["fixture"],
                mibs=_format_float(row.get("throughput_mib_s"), 2),
                wall=_format_float(row.get("conversion_wall_s"), 3),
                missed=_format_float(async_gate.get("missed_beat_pct"), 2),
                maxd=_format_float(async_gate.get("max_delay_ms"), 2),
                p99=_format_float(async_gate.get("p99_delay_ms"), 2),
                ttfo=_format_float((cadence.get("first_chunk_s") or 0) * 1000, 2)
                if cadence
                else "—",
                gap=_format_float(cadence.get("max_inter_chunk_gap_s") * 1000, 2)
                if cadence and cadence.get("max_inter_chunk_gap_s") is not None
                else "—",
                chunks=cadence.get("chunk_count", "—") if cadence else "—",
                ratio=_format_float(row.get("output_to_input_ratio"), 3),
                rss=_format_float(
                    (row.get("ru_maxrss_delta_bytes") or 0) / 1024 / 1024, 1
                ),
                apass="yes" if async_gate.get("passes_v1_worker_async") else "no",
            )
        )
    lines.append("")
    lines.append("## Gate v1 evaluation")
    lines.append("")
    lines.append(
        "| Adapter | Throughput | Async | RSS | Streaming TTFO | Fidelity prelim | Passes all |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for adapter, ev in result["gate"]["adapter_evaluations"].items():
        lines.append(
            f"| {adapter} | {ev['throughput_pass']} | {ev['async_pass']} | {ev['rss_one_shot_pass']} | {ev['streaming_ttfo_pass']} | {ev['fidelity_options_prelim_pass']} | {ev['passes_all_v1']} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in result["gate"].get("notes", []):
        lines.append(f"- {note}")
    lines.append(
        "- `output_to_input_ratio` is included to catch silent truncation/flat output curves across fixture sizes."
    )
    path.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sizes", nargs="+", default=list(FIXTURE_ORDER), choices=list(FIXTURE_ORDER)
    )
    parser.add_argument("--adapters", nargs="+", default=list(DEFAULT_ADAPTERS))
    parser.add_argument("--timeout-s", type=float, default=900.0)
    parser.add_argument("--interval-s", type=float, default=0.005)
    parser.add_argument("--output", type=Path, default=PHASE1_JSON)
    parser.add_argument("--report", type=Path, default=PHASE1_REPORT)
    args = parser.parse_args(argv)

    unknown = set(args.adapters) - _known_adapter_names()
    if unknown:
        raise SystemExit(f"unknown adapters: {sorted(unknown)}")

    fixtures = load_fixture_set(names=tuple(args.sizes))
    requests = [
        RowRequest(adapter, fixture.name, fixture.path)
        for fixture in fixtures.fixtures
        for adapter in args.adapters
    ]
    rows: list[dict[str, Any]] = []
    for index, request in enumerate(requests, start=1):
        print(
            f"[{index}/{len(requests)}] {request.adapter} × {request.fixture_name}",
            flush=True,
        )
        row = _run_row(request, interval_s=args.interval_s, timeout_s=args.timeout_s)
        rows.append(row)
        if row.get("status") == "ok":
            print(
                f"  ok {row.get('conversion_wall_s'):.3f}s {row.get('throughput_mib_s'):.2f} MiB/s "
                f"missed={row['async_gate']['missed_beat_pct']:.2f}% max={row['async_gate']['max_delay_ms']:.2f}ms",
                flush=True,
            )
        else:
            print(f"  {row.get('status')} {row.get('stderr', '')[:200]}", flush=True)

    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "fixture_manifest": "benchmarks/fixtures.lock.json",
        "manifest_naming": "benchmarks/fixtures.lock.json is the canonical fixture manifest; no separate benchmarks/fixtures/manifest.json is used.",
        "sizes": args.sizes,
        "adapters": args.adapters,
        "rows": rows,
        "gate": _evaluate_gate(rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_report(result, args.report)
    print(f"wrote {args.output} and {args.report}")


if __name__ == "__main__":
    main()
