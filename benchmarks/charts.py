"""Generate phase-3 comparison charts from ``benchmarks/results/phase3.json``.

Usage:
    python benchmarks/charts.py benchmarks/results/phase3.json

The script writes PNGs into ``benchmarks/results/charts/`` by default. It is kept
separate from the benchmark runner so final chart generation can be re-run without
re-running the expensive matrix.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

FIXTURE_ORDER = ("small", "medium", "large", "xlarge")
CHART_FILENAMES = {
    "throughput": "throughput_by_size.png",
    "memory": "memory_scaling_peak_rss.png",
    "async": "async_stalls.png",
    "ttfo": "ttfo_cadence.png",
}


def _load_pyplot():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without dep
        raise SystemExit(
            "matplotlib is required to generate phase-3 charts; install the benchmark "
            "extras/dependency group before running benchmarks/charts.py"
        ) from exc
    return plt


def _fixture_sort_key(name: str) -> tuple[int, str]:
    try:
        return (FIXTURE_ORDER.index(name), name)
    except ValueError:
        return (len(FIXTURE_ORDER), name)


def _rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in result.get("rows", []) if row.get("status") == "ok"]


def _adapters(rows: list[dict[str, Any]]) -> list[str]:
    seen: dict[str, None] = {}
    for row in rows:
        seen.setdefault(row["adapter"], None)
    return list(seen)


def _fixtures(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({row["fixture"] for row in rows}, key=_fixture_sort_key)


def _mib(value: float | int | None) -> float | None:
    return None if value is None else float(value) / 1024 / 1024


def _save(fig, output_dir: Path, filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    return path


def plot_throughput(result: dict[str, Any], output_dir: Path) -> Path:
    plt = _load_pyplot()
    rows = _rows(result)
    adapters = _adapters(rows)
    fixtures = _fixtures(rows)
    by_key = {(row["adapter"], row["fixture"]): row for row in rows}

    fig, ax = plt.subplots(figsize=(12, 6))
    x = list(range(len(fixtures)))
    width = 0.8 / max(len(adapters), 1)
    for idx, adapter in enumerate(adapters):
        offset = (idx - (len(adapters) - 1) / 2) * width
        values = [
            (by_key.get((adapter, fixture), {}).get("throughput_mib_s") or 0.0)
            for fixture in fixtures
        ]
        ax.bar([pos + offset for pos in x], values, width=width, label=adapter)
    ax.set_title("Phase 3 throughput by fixture size")
    ax.set_ylabel("MiB/s")
    ax.set_xlabel("Fixture")
    ax.set_xticks(x)
    ax.set_xticklabels(fixtures)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize="small", ncols=2)
    path = _save(fig, output_dir, CHART_FILENAMES["throughput"])
    plt.close(fig)
    return path


def plot_memory_scaling(result: dict[str, Any], output_dir: Path) -> Path:
    plt = _load_pyplot()
    rows = _rows(result)
    fixtures = _fixtures(rows)
    adapters = _adapters(rows)
    by_key = {(row["adapter"], row["fixture"]): row for row in rows}

    fig, ax = plt.subplots(figsize=(12, 6))
    x = list(range(len(fixtures)))
    for adapter in adapters:
        values = []
        for fixture in fixtures:
            row = by_key.get((adapter, fixture), {})
            rss_bytes = row.get("peak_rss_delta_bytes") or row.get(
                "ru_maxrss_delta_bytes"
            )
            values.append(_mib(rss_bytes) or 0.0)
        ax.plot(x, values, marker="o", label=adapter)
    ax.set_title("Peak RSS memory scaling across fixture sizes")
    ax.set_ylabel("Peak RSS Δ (MiB)")
    ax.set_xlabel("Fixture")
    ax.set_xticks(x)
    ax.set_xticklabels(fixtures)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize="small", ncols=2)
    path = _save(fig, output_dir, CHART_FILENAMES["memory"])
    plt.close(fig)
    return path


def plot_async_stalls(result: dict[str, Any], output_dir: Path) -> Path:
    plt = _load_pyplot()
    rows = _rows(result)
    adapters = _adapters(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["adapter"]].append(row)

    max_delay = []
    missed = []
    for adapter in adapters:
        adapter_rows = grouped[adapter]
        max_delay.append(
            max(
                (row.get("async_gate", {}).get("max_delay_ms") or 0.0)
                for row in adapter_rows
            )
        )
        missed.append(
            max(
                (row.get("async_gate", {}).get("missed_beat_pct") or 0.0)
                for row in adapter_rows
            )
        )

    fig, ax = plt.subplots(figsize=(12, 6))
    x = list(range(len(adapters)))
    ax.bar([pos - 0.2 for pos in x], max_delay, width=0.4, label="max stall ms")
    ax2 = ax.twinx()
    ax2.bar(
        [pos + 0.2 for pos in x],
        missed,
        width=0.4,
        color="tab:orange",
        label="missed beat %",
    )
    ax.set_title("Worst-case async stalls by adapter")
    ax.set_ylabel("Max stall (ms)")
    ax2.set_ylabel("Missed beat %")
    ax.set_xticks(x)
    ax.set_xticklabels(adapters, rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", fontsize="small")
    ax2.legend(loc="upper right", fontsize="small")
    path = _save(fig, output_dir, CHART_FILENAMES["async"])
    plt.close(fig)
    return path


def plot_ttfo(result: dict[str, Any], output_dir: Path) -> Path:
    plt = _load_pyplot()
    rows = [row for row in _rows(result) if row.get("streaming_cadence")]
    fixtures = _fixtures(rows)
    adapters = _adapters(rows)
    by_key = {(row["adapter"], row["fixture"]): row for row in rows}

    fig, ax = plt.subplots(figsize=(10, 5))
    if not rows:
        ax.set_title("Streaming TTFO/cadence (no streaming rows present)")
        ax.text(0.5, 0.5, "No streaming_cadence rows", ha="center", va="center")
        ax.set_axis_off()
    else:
        x = list(range(len(fixtures)))
        width = 0.8 / max(len(adapters), 1)
        for idx, adapter in enumerate(adapters):
            offset = (idx - (len(adapters) - 1) / 2) * width
            values = []
            for fixture in fixtures:
                cadence = (
                    by_key.get((adapter, fixture), {}).get("streaming_cadence") or {}
                )
                first_chunk_s = cadence.get("first_chunk_s")
                values.append((first_chunk_s or 0.0) * 1000)
            ax.bar(
                [pos + offset for pos in x],
                values,
                width=width,
                label=f"{adapter} TTFO",
            )
        ax.set_title("Streaming time-to-first-output by fixture size")
        ax.set_ylabel("TTFO (ms)")
        ax.set_xlabel("Fixture")
        ax.set_xticks(x)
        ax.set_xticklabels(fixtures)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize="small")
    path = _save(fig, output_dir, CHART_FILENAMES["ttfo"])
    plt.close(fig)
    return path


def generate_charts(phase3_json: Path, output_dir: Path | None = None) -> list[Path]:
    result = json.loads(phase3_json.read_text())
    out = output_dir or phase3_json.parent / "charts"
    return [
        plot_throughput(result, out),
        plot_memory_scaling(result, out),
        plot_async_stalls(result, out),
        plot_ttfo(result, out),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase3_json", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    for path in generate_charts(args.phase3_json, args.output_dir):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
