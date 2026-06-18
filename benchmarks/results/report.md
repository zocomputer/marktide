# Phase 1 HTML→Markdown benchmark report

Generated: `2026-06-18T09:05:00-0700`
Gate: `v1`
Fixture manifest: `/Users/dcosson/h2home/projects/new-html-parser/benchmarks/fixtures.lock.json` (canonical; no separate `manifest.json` is used)

## Verdict: BUILD phase 2

Throughput is a warm single-conversion measurement after a tiny adapter warmup; output hash/bytes and heartbeat metrics describe that exact conversion. Native streaming adapters additionally report TTFO and inter-chunk cadence from their streaming API.

## Matrix results

| Adapter | Fixture | Status | MiB/s | Wall s | Missed beat % | Max delay ms | p99 delay ms | TTFO ms | Max stream gap ms | Stream chunks | Output/Input | Peak RSS Δ MiB | RSS/Input | Async pass |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| markdownify | small | ok | 6.71 | 0.015 | 0.00 | 9.60 | 9.60 | — | — | — | 0.915 | 2.8 | 28.86 | yes |
| html_to_markdown | small | ok | 24.17 | 0.004 | 0.00 | 0.14 | 0.14 | — | — | — | 0.915 | 1.6 | 16.58 | yes |
| htmd_py | small | ok | 44.97 | 0.002 | 0.00 | 0.25 | 0.25 | — | — | — | 0.916 | 1.5 | 15.47 | yes |
| html2text_rs | small | ok | 35.59 | 0.003 | 0.00 | 0.31 | 0.31 | — | — | — | 0.916 | 2.1 | 21.53 | yes |
| marktide | small | ok | 52.10 | 0.002 | 0.00 | 0.33 | 0.33 | — | — | — | 0.916 | 0.9 | 9.09 | yes |
| marktide_streaming | small | ok | 58.95 | 0.002 | 0.00 | 0.46 | 0.46 | 0.82 | 0.50 | 2 | 0.916 | 0.8 | 7.65 | yes |
| lxml_naive | small | ok | 27.55 | 0.004 | 0.00 | 0.22 | 0.22 | — | — | — | 0.908 | 0.8 | 8.13 | yes |
| markdownify | medium | ok | 3.91 | 1.367 | 66.27 | 28.20 | 28.20 | — | — | — | 0.379 | 138.1 | 25.83 | no |
| html_to_markdown | medium | ok | 22.09 | 0.242 | 50.00 | 236.97 | 236.97 | — | — | — | 1.717 | 209.8 | 39.24 | no |
| htmd_py | medium | ok | 65.12 | 0.082 | 100.00 | 77.15 | 77.15 | — | — | — | 0.734 | 80.6 | 15.07 | no |
| html2text_rs | medium | ok | 34.81 | 0.154 | 0.00 | 0.71 | 0.71 | — | — | — | 0.627 | 190.4 | 35.61 | yes |
| marktide | medium | ok | 23.17 | 0.231 | 0.00 | 0.94 | 0.94 | — | — | — | 0.379 | 23.0 | 4.31 | yes |
| marktide_streaming | medium | ok | 22.70 | 0.236 | 0.00 | 8.08 | 8.08 | 2.09 | 20.06 | 12 | 0.379 | 14.7 | 2.74 | yes |
| lxml_naive | medium | ok | 73.64 | 0.073 | 22.22 | 16.74 | 16.74 | — | — | — | 0.239 | 61.1 | 11.42 | no |
| markdownify | large | ok | 2.71 | 20.280 | 62.35 | 281.63 | 32.06 | — | — | — | 0.379 | 1405.0 | 25.58 | no |
| html_to_markdown | large | ok | 23.28 | 2.360 | 50.00 | 2354.28 | 2354.28 | — | — | — | 1.717 | 2146.6 | 39.08 | no |
| htmd_py | large | ok | 66.56 | 0.825 | 50.00 | 820.17 | 820.17 | — | — | — | 0.734 | 786.3 | 14.32 | no |
| html2text_rs | large | ok | 37.52 | 1.464 | 0.78 | 33.72 | 6.52 | — | — | — | 0.634 | 1957.3 | 35.64 | no |
| marktide | large | ok | 23.19 | 2.369 | 0.24 | 12.00 | 1.15 | — | — | — | 0.379 | 228.6 | 4.16 | yes |
| marktide_streaming | large | ok | 23.58 | 2.330 | 0.24 | 10.01 | 1.12 | 1.97 | 25.55 | 114 | 0.379 | 124.5 | 2.27 | yes |
| lxml_naive | large | ok | 71.49 | 0.768 | 10.99 | 101.62 | 101.62 | — | — | — | 0.239 | 621.1 | 11.31 | no |
| markdownify | xlarge | ok | 2.01 | 54.549 | 60.39 | 512.69 | 17.83 | — | — | — | 0.379 | 2811.1 | 25.59 | no |
| html_to_markdown | xlarge | ok | 22.96 | 4.784 | 50.00 | 4778.20 | 4778.20 | — | — | — | 1.717 | 3761.0 | 34.24 | no |
| htmd_py | xlarge | ok | 64.10 | 1.714 | 50.00 | 1708.69 | 1708.69 | — | — | — | 0.734 | 1569.2 | 14.29 | no |
| html2text_rs | xlarge | ok | 36.22 | 3.033 | 0.38 | 71.58 | 1.63 | — | — | — | 0.635 | 3906.7 | 35.57 | no |
| marktide | xlarge | ok | 23.15 | 4.746 | 0.12 | 18.82 | 1.25 | — | — | — | 0.379 | 453.3 | 4.13 | no |
| marktide_streaming | xlarge | ok | 23.24 | 4.727 | 0.00 | 8.83 | 1.10 | 2.16 | 31.58 | 227 | 0.379 | 247.3 | 2.25 | yes |
| lxml_naive | xlarge | ok | 70.32 | 1.562 | 13.07 | 200.64 | 26.23 | — | — | — | 0.239 | 1238.8 | 11.28 | no |

## Memory scaling

| Adapter | Fixture | Input MiB | Peak RSS Δ MiB | RSS/Input | Samples |
|---|---:|---:|---:|---:|---:|
| markdownify | small | 0.10 | 2.8 | 28.86 | 3 |
| markdownify | medium | 5.35 | 138.1 | 25.83 | 45 |
| markdownify | large | 54.92 | 1405.0 | 25.58 | 607 |
| markdownify | xlarge | 109.85 | 2811.1 | 25.59 | 1669 |
| html_to_markdown | small | 0.10 | 1.6 | 16.58 | 3 |
| html_to_markdown | medium | 5.35 | 209.8 | 39.24 | 4 |
| html_to_markdown | large | 54.92 | 2146.6 | 39.08 | 4 |
| html_to_markdown | xlarge | 109.85 | 3761.0 | 34.24 | 4 |
| htmd_py | small | 0.10 | 1.5 | 15.47 | 3 |
| htmd_py | medium | 5.35 | 80.6 | 15.07 | 3 |
| htmd_py | large | 54.92 | 786.3 | 14.32 | 4 |
| htmd_py | xlarge | 109.85 | 1569.2 | 14.29 | 4 |
| html2text_rs | small | 0.10 | 2.1 | 21.53 | 3 |
| html2text_rs | medium | 5.35 | 190.4 | 35.61 | 10 |
| html2text_rs | large | 54.92 | 1957.3 | 35.64 | 74 |
| html2text_rs | xlarge | 109.85 | 3906.7 | 35.57 | 148 |
| marktide | small | 0.10 | 0.9 | 9.09 | 3 |
| marktide | medium | 5.35 | 23.0 | 4.31 | 14 |
| marktide | large | 54.92 | 228.6 | 4.16 | 119 |
| marktide | xlarge | 109.85 | 453.3 | 4.13 | 235 |
| marktide_streaming | small | 0.10 | 0.8 | 7.65 | 3 |
| marktide_streaming | medium | 5.35 | 14.7 | 2.74 | 14 |
| marktide_streaming | large | 54.92 | 124.5 | 2.27 | 116 |
| marktide_streaming | xlarge | 109.85 | 247.3 | 2.25 | 234 |
| lxml_naive | small | 0.10 | 0.8 | 8.13 | 3 |
| lxml_naive | medium | 5.35 | 61.1 | 11.42 | 6 |
| lxml_naive | large | 54.92 | 621.1 | 11.31 | 32 |
| lxml_naive | xlarge | 109.85 | 1238.8 | 11.28 | 60 |

## Gate v1 evaluation

| Adapter | Throughput | Async | RSS | Streaming TTFO | Fidelity prelim | Passes all |
|---|---|---|---|---|---|---|
| html_to_markdown | True | False | False | False | True | False |
| htmd_py | True | False | False | False | True | False |
| html2text_rs | True | False | False | False | False | False |
| marktide | True | False | False | False | True | False |
| marktide_streaming | True | True | False | True | True | False |
| lxml_naive | True | False | False | False | False | False |

## Notes

- TTFO criterion is measured only for adapters exposing streaming_cadence; one-shot-only libraries structurally fail it.
- Fidelity is preliminary here; tests/conformance differential harness owns exact conformance scoring.
- `output_to_input_ratio` is included to catch silent truncation/flat output curves across fixture sizes.
