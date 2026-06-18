# Code Review: zo-1fp.17 (R1, reviewer-leaf)

- Bead: zo-1fp.17
- Commit range: 406c17a (reviewed on current `main`, with later review-only/cleanup commits present)
- Plan doc: docs/design.md / benchmark harness deliverables
- Reviewer: reviewer-leaf
- Review commit: f1e0a6b

## Findings

No findings.

## Verification

Validated `benchmarks/results/phase3.json`, `benchmarks/results/report.md`, and `benchmarks/results/charts/*.png`:

1. **Row coverage and internal arithmetic.** `benchmarks/results/phase3.json` contains 28 ok rows: 7 adapters × 4 fixtures, with no missing or extra adapter/fixture pairs. For every row, `throughput_mib_s` matches `input_bytes / conversion_wall_s / MiB` within rounding tolerance.
2. **Dead-code-benchmark guard.** Every performance row has a 64-character `output_hash`. For every fixture, `html2md` and `html2md_streaming` output hashes match, and `html2md_streaming.streaming_cadence.output_hash` matches the row output hash.
3. **Headline performance claims.** The xlarge values in `benchmarks/results/report.md` are supported by JSON:
   - `html2md_streaming`: 5.994s, 18.325 MiB/s, 244.703 MiB peak RSS delta, 0.00% missed beats, 5.424ms max stall.
   - `markdownify`: 53.435s, 2.056 MiB/s, 2808.906 MiB peak RSS delta, 70.020% missed beats, 500.108ms max stall.
   - Derived ratios: 8.914× wall-time win and 11.479× lower peak RSS delta.
4. **Streaming latency claims.** `html2md_streaming` xlarge cadence in JSON supports TTFO 2.421ms, 227 chunks, and max inter-chunk gap 29.508ms.
5. **Conformance claims.** `tests/conformance/reports/latest.json` supports the phase-3 snapshot claim of raw primary `html2md` / `html2md_streaming` fidelity 294/298 = 98.658%; counting the two documented primary lxml/browser parser divergences yields 296/298 = 99.329% effective fidelity as reported.
6. **Charts match JSON.** Regenerated all charts from `benchmarks/results/phase3.json` into a temp directory with `uv run --group benchmark python benchmarks/charts.py ... --output-dir ...`; all four PNGs were byte-identical to committed charts:
   - `async_stalls.png`
   - `memory_scaling_peak_rss.png`
   - `throughput_by_size.png`
   - `ttfo_cadence.png`

## Checks run

- Custom JSON/report/chart validation script against `benchmarks/results/phase3.json`, `benchmarks/results/report.md`, `benchmarks/results/charts/*.png`, and `tests/conformance/reports/latest.json`.
- `uv run --group benchmark python benchmarks/charts.py benchmarks/results/phase3.json --output-dir <tmp>` for chart regeneration comparison.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
