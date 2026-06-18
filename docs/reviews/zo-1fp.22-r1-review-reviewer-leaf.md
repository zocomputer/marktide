# Code Review: zo-1fp.22 (R1, reviewer-leaf)

- Bead: zo-1fp.22
- Commit range: 3979240 plus c078e2c
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: c7bd68b

## Findings

No findings.

## Positive notes

- `benchmarks/pyproject.toml:1-34` defines a self-contained uv project with committed `benchmarks/uv.lock`, installs `markdownify`, `html-to-markdown==3.5.7`, `htmd-py`, `html2text-rs`, and resolves local `html2md` as an editable path dependency via `[tool.uv.sources] html2md = { path = "..", editable = true }`.
- `benchmarks/bench.py:97-146` implements `uv run bench` / `uv run bench --full`; the quick path runs small+medium across the seven documented contenders and prints the async-starvation and headline comparison blocks.
- `benchmarks/bench.py:149-165` implements `uv run bench-async-starvation`; the command prints the requested markdownify-vs-`html2md_streaming` heartbeat proof.
- `benchmarks/README.md:8-116` documents the self-contained setup, quick verification, full matrix, async-starvation-only command, direct harness commands, lockfile, pinned `html-to-markdown==3.5.7`, and editable parent `html2md` path dependency.
- `benchmarks/results/report.md:129-137` now reconciles the phase-3 conformance section to the canonical final fidelity numbers: `html2md` and `html2md_streaming` at `296/298` raw = `99.329%`, effective `100.000%`.

## Checks run

- `cd benchmarks && uv sync`
- `cd benchmarks && uv run bench`
  - Verified all seven contenders ran on small+medium.
  - Medium async headline printed `markdownify` missed `73.61%` heartbeats and `html2md_streaming` missed `0.00%` with TTFO `2.32ms`.
- `cd benchmarks && uv run bench-async-starvation`
  - Printed `markdownify` missed `74.29%` heartbeats and `html2md_streaming` missed `0.00%` with TTFO `2.51ms`.
- `cd benchmarks && uv run pytest -q` — `15 passed`.
- Inspected `benchmarks/uv.lock` for the editable `html2md` source and comparison-library resolved packages.
- Checked `benchmarks/results/report.md:129-137` for the refreshed `296/298` raw and `100.000%` effective fidelity values.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
