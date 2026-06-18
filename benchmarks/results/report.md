# Phase 1 HTML→Markdown benchmark report

Generated: `2026-06-17T22:04:24-0700`
Gate: `v1`
Fixture manifest: `benchmarks/fixtures.lock.json` (canonical; no separate `manifest.json` is used)

## Verdict: BUILD phase 2

No existing library in this matrix satisfies all gate v1 criteria. In particular, all existing candidates are one-shot and therefore structurally fail the streaming TTFO/cadence criterion. Throughput is a warm single-conversion measurement after a tiny adapter warmup; output hash/bytes and heartbeat metrics describe that exact conversion.

## Matrix results

| Adapter | Fixture | Status | MiB/s | Wall s | Missed beat % | Max delay ms | p99 delay ms | Output/Input | RSS delta MiB | Async pass |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| markdownify | small | ok | 7.89 | 0.012 | 0.00 | 7.47 | 7.47 | 0.915 | 3.0 | yes |
| html_to_markdown | small | ok | 37.22 | 0.003 | 0.00 | 0.62 | 0.62 | 0.915 | 1.7 | yes |
| htmd_py | small | ok | 78.89 | 0.001 | 0.00 | 1.03 | 1.03 | 0.916 | 1.3 | yes |
| html2text_rs | small | ok | 39.81 | 0.002 | 0.00 | 0.67 | 0.67 | 0.916 | 1.9 | yes |
| lxml_naive | small | ok | 143.83 | 0.001 | 0.00 | 1.14 | 1.14 | 0.908 | 0.7 | yes |
| markdownify | medium | ok | 4.07 | 1.314 | 98.48 | 32.62 | 32.62 | 0.379 | 138.0 | no |
| html_to_markdown | medium | ok | 23.39 | 0.229 | 100.00 | 223.65 | 223.65 | 1.717 | 211.2 | no |
| htmd_py | medium | ok | 65.59 | 0.082 | 100.00 | 76.57 | 76.57 | 0.734 | 80.5 | no |
| html2text_rs | medium | ok | 36.69 | 0.146 | 0.00 | 1.31 | 1.31 | 0.627 | 190.2 | yes |
| lxml_naive | medium | ok | 74.14 | 0.072 | 22.22 | 16.31 | 16.31 | 0.239 | 61.1 | no |
| markdownify | large | ok | 2.81 | 19.515 | 99.68 | 263.33 | 43.45 | 0.379 | 1405.0 | no |
| html_to_markdown | large | ok | 24.17 | 2.272 | 50.00 | 2266.99 | 2266.99 | 1.717 | 2152.0 | no |
| htmd_py | large | ok | 67.76 | 0.811 | 50.00 | 805.53 | 805.53 | 0.734 | 786.2 | no |
| html2text_rs | large | ok | 38.23 | 1.436 | 0.85 | 32.53 | 1.31 | 0.634 | 1953.1 | no |
| lxml_naive | large | ok | 73.34 | 0.749 | 19.23 | 104.42 | 104.42 | 0.239 | 621.0 | no |
| markdownify | xlarge | ok | 2.09 | 52.537 | 99.88 | 490.54 | 16.43 | 0.379 | 2810.8 | no |
| html_to_markdown | xlarge | ok | 25.06 | 4.383 | 50.00 | 4377.57 | 4377.57 | 1.717 | 4295.0 | no |
| htmd_py | xlarge | ok | 68.70 | 1.599 | 50.00 | 1593.93 | 1593.93 | 0.734 | 1567.9 | no |
| html2text_rs | xlarge | ok | 38.88 | 2.825 | 0.44 | 67.52 | 1.32 | 0.635 | 3905.1 | no |
| lxml_naive | xlarge | ok | 75.45 | 1.456 | 19.05 | 173.62 | 32.95 | 0.239 | 1238.5 | no |

## Gate v1 evaluation

| Adapter | Throughput | Async | RSS | Streaming TTFO | Fidelity prelim | Passes all |
|---|---|---|---|---|---|---|
| html_to_markdown | True | False | False | False | True | False |
| htmd_py | True | False | False | False | True | False |
| html2text_rs | True | False | False | False | False | False |
| lxml_naive | True | False | False | False | False | False |

## Notes

- TTFO criterion is structurally failed for all existing one-shot libraries in this phase-1 matrix.
- Fidelity is preliminary here; tests/conformance differential harness owns exact conformance scoring.
- `output_to_input_ratio` is included to catch silent truncation/flat output curves across fixture sizes.
