"""Command-line entry points for the reproducible benchmark project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from charts import generate_charts
from harness import runner

BENCHMARKS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCHMARKS_DIR / "results"
DEFAULT_VERIFY_SIZES = ("small", "medium")
FULL_SIZES = ("small", "medium", "large", "xlarge")
DEFAULT_ADAPTERS = (
    "markdownify",
    "html_to_markdown",
    "htmd_py",
    "html2text_rs",
    "marktide",
    "marktide_streaming",
    "lxml_naive",
)
ASYNC_ADAPTERS = ("markdownify", "marktide_streaming")


def _read_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows_by_adapter(result: dict[str, Any], fixture: str) -> dict[str, dict[str, Any]]:
    return {
        row["adapter"]: row
        for row in result.get("rows", [])
        if row.get("status") == "ok" and row.get("fixture") == fixture
    }


def _print_async_starvation_summary(result: dict[str, Any], fixture: str) -> None:
    rows = _rows_by_adapter(result, fixture)
    print("")
    print("=== ASYNC-LOOP STARVATION PROOF (benchmark harness heartbeat) ===")
    print(
        "This is measured by benchmarks/harness/probe.py while conversion runs in a "
        "worker thread; it is not an e2e test."
    )
    for adapter in ASYNC_ADAPTERS:
        row = rows[adapter]
        gate = row["async_gate"]
        cadence = row.get("streaming_cadence") or {}
        ttfo = cadence.get("first_chunk_s")
        ttfo_text = f", TTFO={ttfo * 1000:.2f}ms" if ttfo is not None else ""
        print(
            f"{adapter:18s} {fixture:7s}: missed={gate['missed_beat_pct']:.2f}% "
            f"max_stall={gate['max_delay_ms']:.2f}ms "
            f"p99={gate['p99_delay_ms']:.2f}ms{ttfo_text}"
        )
    print("Expected headline: marktide_streaming ~= 0% missed beats; markdownify is high on medium+.")


def _print_headline_summary(result: dict[str, Any], fixture: str) -> None:
    rows = _rows_by_adapter(result, fixture)
    markdownify = rows["markdownify"]
    streaming = rows["marktide_streaming"]
    speedup = markdownify["conversion_wall_s"] / streaming["conversion_wall_s"]
    print("")
    print("=== HEADLINE COMPARISON ===")
    print(
        f"marktide_streaming {fixture}: {streaming['conversion_wall_s']:.3f}s, "
        f"{streaming['throughput_mib_s']:.2f} MiB/s"
    )
    print(
        f"markdownify        {fixture}: {markdownify['conversion_wall_s']:.3f}s, "
        f"{markdownify['throughput_mib_s']:.2f} MiB/s"
    )
    print(f"Wall-time speedup on {fixture}: {speedup:.1f}x")


def _run_matrix(
    *,
    sizes: tuple[str, ...],
    adapters: tuple[str, ...],
    output: Path,
    report: Path,
    timeout_s: float,
) -> dict[str, Any]:
    runner.main(
        [
            "--sizes",
            *sizes,
            "--adapters",
            *adapters,
            "--output",
            str(output),
            "--report",
            str(report),
            "--timeout-s",
            str(timeout_s),
            "--interval-s",
            "0.005",
            "--memory-interval-s",
            "0.02",
        ]
    )
    return _read_result(output)


def verify(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the reproducible benchmark verification matrix."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="run small→xlarge instead of the quick small+medium verification",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--timeout-s", type=float, default=1800.0)
    args = parser.parse_args(argv)

    sizes = FULL_SIZES if args.full else DEFAULT_VERIFY_SIZES
    output = args.output or RESULTS_DIR / ("phase3-repro.json" if args.full else "verify.json")
    report = args.report or RESULTS_DIR / ("phase3-repro.md" if args.full else "verify.md")
    result = _run_matrix(
        sizes=sizes,
        adapters=DEFAULT_ADAPTERS,
        output=output,
        report=report,
        timeout_s=args.timeout_s,
    )
    fixture = "xlarge" if args.full else "medium"
    _print_async_starvation_summary(result, fixture)
    _print_headline_summary(result, fixture)
    if args.full:
        chart_paths = generate_charts(output)
        print("")
        print("Charts:")
        for path in chart_paths:
            print(f"- {path}")
    print("")
    print(f"JSON:   {output}")
    print(f"Report: {report}")
    return 0


def async_starvation(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run only the markdownify vs marktide_streaming heartbeat proof."
    )
    parser.add_argument("--fixture", choices=FULL_SIZES, default="medium")
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "async-starvation.json")
    parser.add_argument("--report", type=Path, default=RESULTS_DIR / "async-starvation.md")
    parser.add_argument("--timeout-s", type=float, default=900.0)
    args = parser.parse_args(argv)

    result = _run_matrix(
        sizes=(args.fixture,),
        adapters=ASYNC_ADAPTERS,
        output=args.output,
        report=args.report,
        timeout_s=args.timeout_s,
    )
    _print_async_starvation_summary(result, args.fixture)
    _print_headline_summary(result, args.fixture)
    print("")
    print(f"JSON:   {args.output}")
    print(f"Report: {args.report}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--full", action="store_true")
    verify_parser.add_argument("--output", type=Path, default=None)
    verify_parser.add_argument("--report", type=Path, default=None)
    verify_parser.add_argument("--timeout-s", type=float, default=1800.0)
    starvation_parser = subparsers.add_parser("async-starvation")
    starvation_parser.add_argument("--fixture", choices=FULL_SIZES, default="medium")
    starvation_parser.add_argument("--output", type=Path, default=RESULTS_DIR / "async-starvation.json")
    starvation_parser.add_argument("--report", type=Path, default=RESULTS_DIR / "async-starvation.md")
    starvation_parser.add_argument("--timeout-s", type=float, default=900.0)
    args = parser.parse_args(argv)

    if args.command in (None, "verify"):
        verify_args = []
        if getattr(args, "full", False):
            verify_args.append("--full")
        if getattr(args, "output", None) is not None:
            verify_args.extend(["--output", str(args.output)])
        if getattr(args, "report", None) is not None:
            verify_args.extend(["--report", str(args.report)])
        verify_args.extend(["--timeout-s", str(getattr(args, "timeout_s", 1800.0))])
        return verify(verify_args)
    if args.command == "async-starvation":
        starvation_args = [
            "--fixture",
            args.fixture,
            "--output",
            str(args.output),
            "--report",
            str(args.report),
            "--timeout-s",
            str(args.timeout_s),
        ]
        return async_starvation(starvation_args)
    parser.error(f"unknown command: {args.command}")
    return 2


def verify_main() -> int:
    return verify()


def async_starvation_main() -> int:
    return async_starvation()


if __name__ == "__main__":
    raise SystemExit(main())
