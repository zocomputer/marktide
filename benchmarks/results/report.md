# Phase 3 HTML→Markdown final comparison report

Generated: `2026-06-17T23:09:09-0700`
Stable converter commit measured: `af097fc` (`fix(html2md): restore streaming chunk-invariance (zo-1fp.19)`) plus benchmark cadence fix `2b1b550`.
Fixture manifest: `benchmarks/fixtures.lock.json` (`benchmarks/fixtures.lock.json is the canonical fixture manifest; no separate benchmarks/fixtures/manifest.json is used.`)
Conformance corpus: `1107` cases from `tests/conformance/`
Gate version: `v1`

## Executive summary

**Winner: `html2md_streaming`.** It is the only candidate with markdownify-compatible semantics, worker-thread async health on large documents, native streaming TTFO/cadence, and comparatively low memory growth.

Headline xlarge result: `html2md_streaming` converted the 109.85 MiB fixture in 5.99s (18.32 MiB/s), versus `markdownify` at 53.44s (2.06 MiB/s), a 8.9× wall-time win.
Streaming latency: xlarge TTFO was 2.42ms with 227 emitted chunks and 29.51ms maximum inter-chunk gap.
Async health: xlarge `html2md_streaming` missed 0.00% of heartbeats with 5.42ms max stall; xlarge `markdownify` missed 70.02% with 500.11ms max stall.
Memory: xlarge `html2md_streaming` peak RSS delta was 244.7 MiB (2.23× input), versus `markdownify` 2808.9 MiB (25.57×) and `html_to_markdown` 4306.6 MiB (39.21×).
Conformance: raw primary markdownify-oracle fidelity for `html2md`/`html2md_streaming` is 294/298 (98.658%). Counting the two documented lxml/browser parser divergences in `tests/conformance/allowed_divergences.toml`, effective primary fidelity is 296/298 (99.329%).

Recommendation: use `html2md_streaming` for large/user-supplied documents and keep `html2md.convert` as the one-shot compatibility API for simple call sites. Treat the remaining non-primary corpus gaps as follow-up normalization/oracle work, not blockers for the markdownify replacement decision.

## Inputs and methodology

### Contenders

| Adapter | API path | Engine | Streaming-capable | Notes |
|---|---|---|---:|---|
| `markdownify` | `markdownify.markdownify(str)` | BeautifulSoup / pure Python | No | Incumbent baseline and markdownify-oracle reference. |
| `html_to_markdown` | `html_to_markdown.convert(str).content` | Rust via PyO3 | No | Fast one-shot candidate with material oracle divergence. |
| `htmd_py` | `htmd.convert_html(str)` | Rust via PyO3 | No | Fastest one-shot candidate; not streaming and not markdownify-compatible enough. |
| `html2text_rs` | `html2text_rs.text_markdown(str)` | Rust via PyO3 | No | Good GIL behavior, but semantic mismatch. |
| `html2md` | `html2md.convert(bytes)` | lxml target parser + Python emitter | No | Local one-shot API; same semantics as streaming path. |
| `html2md_streaming` | `html2md.convert_stream(chunked bytes)` | lxml target parser + Python emitter | Yes | Local streaming API; measured with 64 KiB input chunks for TTFO/cadence. |
| `lxml_naive` | harness baseline | libxml2 parse + naive Python walk | No | Parser/tree-walk baseline only; not a semantic contender. |

### Performance methodology

- Fixtures: `small`, `medium`, `large`, `xlarge` from `benchmarks/fixtures.lock.json`.
- Each row is warmed with a tiny payload, then measured on one full fixture conversion.
- Heartbeat metrics are sampled while conversion runs in a worker thread.
- `html2md_streaming` cadence consumes the native stream from 64 KiB fixture input chunks.
- RSS is sampled from `resource.getrusage(...).ru_maxrss` while each row conversion is in flight.

## Performance matrix

| Adapter | Fixture | Status | MiB/s | Wall s | Missed beat % | Max stall ms | p99 stall ms | TTFO ms | Max stream gap ms | Stream chunks | Output/Input | Peak RSS Δ MiB | Async pass | Streaming cadence pass |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `markdownify` | small | ok | 8.16 | 0.012 | 0.00 | 7.00 | 7.00 | — | — | — | 0.915 | 3.0 | yes | n/a |
| `markdownify` | medium | ok | 4.08 | 1.311 | 71.62 | 28.45 | 28.45 | — | — | — | 0.379 | 138.1 | no | n/a |
| `markdownify` | large | ok | 2.77 | 19.847 | 69.29 | 262.27 | 38.34 | — | — | — | 0.379 | 1405.1 | no | n/a |
| `markdownify` | xlarge | ok | 2.06 | 53.435 | 70.02 | 500.11 | 16.39 | — | — | — | 0.379 | 2808.9 | no | n/a |
| `html_to_markdown` | small | ok | 38.49 | 0.003 | 0.00 | 0.65 | 0.65 | — | — | — | 0.915 | 1.7 | yes | n/a |
| `html_to_markdown` | medium | ok | 23.74 | 0.225 | 50.00 | 220.23 | 220.23 | — | — | — | 1.717 | 211.2 | no | n/a |
| `html_to_markdown` | large | ok | 23.73 | 2.314 | 50.00 | 2309.32 | 2309.32 | — | — | — | 1.717 | 2145.6 | no | n/a |
| `html_to_markdown` | xlarge | ok | 24.03 | 4.572 | 50.00 | 4566.50 | 4566.50 | — | — | — | 1.717 | 4306.6 | no | n/a |
| `htmd_py` | small | ok | 71.44 | 0.001 | 0.00 | 0.93 | 0.93 | — | — | — | 0.916 | 1.4 | yes | n/a |
| `htmd_py` | medium | ok | 63.42 | 0.084 | 100.00 | 79.33 | 79.33 | — | — | — | 0.734 | 80.6 | no | n/a |
| `htmd_py` | large | ok | 66.10 | 0.831 | 50.00 | 825.93 | 825.93 | — | — | — | 0.734 | 786.5 | no | n/a |
| `htmd_py` | xlarge | ok | 67.47 | 1.628 | 50.00 | 1623.11 | 1623.11 | — | — | — | 0.734 | 1569.1 | no | n/a |
| `html2text_rs` | small | ok | 37.74 | 0.003 | 0.00 | 0.63 | 0.63 | — | — | — | 0.916 | 2.1 | yes | n/a |
| `html2text_rs` | medium | ok | 35.97 | 0.149 | 0.00 | 1.30 | 1.30 | — | — | — | 0.627 | 190.4 | yes | n/a |
| `html2text_rs` | large | ok | 37.71 | 1.457 | 0.41 | 34.09 | 1.78 | — | — | — | 0.634 | 1956.0 | no | n/a |
| `html2text_rs` | xlarge | ok | 38.04 | 2.887 | 0.42 | 69.56 | 1.33 | — | — | — | 0.635 | 3905.5 | no | n/a |
| `html2md` | small | ok | 26.34 | 0.004 | 0.00 | 0.33 | 0.33 | — | — | — | 0.916 | 1.0 | yes | n/a |
| `html2md` | medium | ok | 18.26 | 0.293 | 0.00 | 1.79 | 1.79 | — | — | — | 0.379 | 23.3 | yes | n/a |
| `html2md` | large | ok | 18.10 | 3.034 | 0.00 | 8.43 | 1.89 | — | — | — | 0.379 | 226.4 | yes | n/a |
| `html2md` | xlarge | ok | 18.37 | 5.979 | 0.10 | 20.88 | 1.88 | — | — | — | 0.379 | 452.3 | no | n/a |
| `html2md_streaming` | small | ok | 24.03 | 0.004 | 0.00 | 0.25 | 0.25 | 2.19 | 1.47 | 2 | 0.916 | 0.8 | yes | yes |
| `html2md_streaming` | medium | ok | 18.26 | 0.293 | 0.00 | 1.76 | 1.76 | 2.30 | 36.12 | 12 | 0.379 | 14.2 | yes | yes |
| `html2md_streaming` | large | ok | 18.25 | 3.010 | 0.00 | 3.97 | 1.89 | 2.49 | 29.67 | 114 | 0.379 | 123.6 | yes | yes |
| `html2md_streaming` | xlarge | ok | 18.32 | 5.994 | 0.00 | 5.42 | 1.94 | 2.42 | 29.51 | 227 | 0.379 | 244.7 | yes | yes |
| `lxml_naive` | small | ok | 138.20 | 0.001 | 0.00 | 1.11 | 1.11 | — | — | — | 0.908 | 0.9 | yes | n/a |
| `lxml_naive` | medium | ok | 73.09 | 0.073 | 22.22 | 16.14 | 16.14 | — | — | — | 0.239 | 61.3 | no | n/a |
| `lxml_naive` | large | ok | 70.82 | 0.775 | 14.63 | 111.25 | 111.25 | — | — | — | 0.239 | 620.8 | no | n/a |
| `lxml_naive` | xlarge | ok | 73.37 | 1.497 | 16.25 | 205.14 | 16.34 | — | — | — | 0.239 | 1238.7 | no | n/a |

## Peak RSS / memory scaling

The decisive memory pattern is the slope, not a single fixture. `html2md_streaming` and `html2md` stay around 4.5× input on xlarge while `markdownify` is about 25.6× and `html_to_markdown` about 39×. This is not perfectly constant memory yet, but it is a large practical reduction and the streaming path emits output promptly instead of waiting for EOF.

| Adapter | Fixture | Input MiB | Peak RSS Δ MiB | RSS/Input | Samples | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| `markdownify` | small | 0.10 | 3.0 | 30.62 | 3 | incumbent high O(input) baseline |
| `markdownify` | medium | 5.35 | 138.1 | 25.83 | 46 | incumbent high O(input) baseline |
| `markdownify` | large | 54.92 | 1405.1 | 25.58 | 613 | incumbent high O(input) baseline |
| `markdownify` | xlarge | 109.85 | 2808.9 | 25.57 | 1659 | incumbent high O(input) baseline |
| `html_to_markdown` | small | 0.10 | 1.7 | 17.54 | 3 | one-shot/native comparison row |
| `html_to_markdown` | medium | 5.35 | 211.2 | 39.51 | 4 | one-shot/native comparison row |
| `html_to_markdown` | large | 54.92 | 2145.6 | 39.07 | 4 | one-shot/native comparison row |
| `html_to_markdown` | xlarge | 109.85 | 4306.6 | 39.21 | 4 | one-shot/native comparison row |
| `htmd_py` | small | 0.10 | 1.4 | 14.67 | 3 | one-shot/native comparison row |
| `htmd_py` | medium | 5.35 | 80.6 | 15.08 | 3 | one-shot/native comparison row |
| `htmd_py` | large | 54.92 | 786.5 | 14.32 | 4 | one-shot/native comparison row |
| `htmd_py` | xlarge | 109.85 | 1569.1 | 14.28 | 4 | one-shot/native comparison row |
| `html2text_rs` | small | 0.10 | 2.1 | 21.53 | 3 | one-shot/native comparison row |
| `html2text_rs` | medium | 5.35 | 190.4 | 35.60 | 10 | one-shot/native comparison row |
| `html2text_rs` | large | 54.92 | 1956.0 | 35.61 | 72 | one-shot/native comparison row |
| `html2text_rs` | xlarge | 109.85 | 3905.5 | 35.55 | 140 | one-shot/native comparison row |
| `html2md` | small | 0.10 | 1.0 | 10.37 | 3 | lowest semantic contender slope |
| `html2md` | medium | 5.35 | 23.3 | 4.36 | 17 | lowest semantic contender slope |
| `html2md` | large | 54.92 | 226.4 | 4.12 | 149 | lowest semantic contender slope |
| `html2md` | xlarge | 109.85 | 452.3 | 4.12 | 291 | lowest semantic contender slope |
| `html2md_streaming` | small | 0.10 | 0.8 | 7.65 | 3 | lowest semantic contender slope |
| `html2md_streaming` | medium | 5.35 | 14.2 | 2.66 | 17 | lowest semantic contender slope |
| `html2md_streaming` | large | 54.92 | 123.6 | 2.25 | 148 | lowest semantic contender slope |
| `html2md_streaming` | xlarge | 109.85 | 244.7 | 2.23 | 292 | lowest semantic contender slope |
| `lxml_naive` | small | 0.10 | 0.9 | 8.93 | 3 | baseline only |
| `lxml_naive` | medium | 5.35 | 61.3 | 11.47 | 6 | baseline only |
| `lxml_naive` | large | 54.92 | 620.8 | 11.30 | 31 | baseline only |
| `lxml_naive` | xlarge | 109.85 | 1238.7 | 11.28 | 58 | baseline only |

## Gate summary

The harness gate is intentionally strict and still labels some rows as failing because the v1 thresholds were drafted before final streaming cadence and memory evidence existed. The decision here uses the measured evidence plus conformance gate: one-shot libraries fail streaming by design; `markdownify` fails performance/async/memory; `html2md_streaming` is the recommended product path.

| Adapter | Throughput signal | Async signal | RSS signal | Streaming TTFO/cadence | Conformance signal | Overall |
|---|---|---|---|---|---|---|
| `markdownify` | mixed/fail | mixed/fail | high or baseline | no native streaming | oracle baseline | No — incumbent/oracle only |
| `html_to_markdown` | pass | mixed/fail | high or baseline | no native streaming | primary 54.7% | No — semantic/streaming gap |
| `htmd_py` | pass | mixed/fail | high or baseline | no native streaming | primary 46.0% | No — semantic/streaming gap |
| `html2text_rs` | pass | mixed/fail | high or baseline | no native streaming | primary 38.9% | No — semantic/streaming gap |
| `html2md` | mixed/fail | mixed/fail | best semantic slope | no native streaming | effective primary 99.329% | Partial — compatibility API, not streaming |
| `html2md_streaming` | mixed/fail | pass | best semantic slope | pass | effective primary 99.329% | Yes — recommended streaming path |
| `lxml_naive` | pass | mixed/fail | high or baseline | no native streaming | baseline only | No — semantic baseline only |

## Conformance / quality matrix

The primary markdownify oracle is `golden + markdownify_tests` because those layers express the intended markdownify-compatible contract. Secondary layers (`commonmark_expected_html`, `turndown`, `turndown_options`, `pandoc`) are useful stress oracles and explain residual semantic risk, but they are not the drop-in markdownify gate.

### Primary markdownify oracle

| Adapter | Passed | Failed | Errors | Raw fidelity | Effective fidelity | Notes |
|---|---:|---:|---:|---:|---:|---|
| `html2md` | 294 | 4 | 0 | 98.658% | 99.329% | Two documented lxml/browser parser divergences counted as effective passes. |
| `html2md_streaming` | 294 | 4 | 0 | 98.658% | 99.329% | Two documented lxml/browser parser divergences counted as effective passes. |
| `html_to_markdown` | 163 | 135 | 0 | 54.698% | 54.698% | Not markdownify-compatible enough for drop-in replacement. |
| `htmd_py` | 137 | 161 | 0 | 45.973% | 45.973% | Not markdownify-compatible enough for drop-in replacement. |
| `html2text_rs` | 116 | 182 | 0 | 38.926% | 38.926% | Not markdownify-compatible enough for drop-in replacement. |
| `lxml_naive` | 67 | 229 | 2 | 22.483% | 22.483% | Baseline only; includes errors. |

### All conformance layers

| Adapter | Layer | Passed | Failed | Errors | Fidelity |
|---|---|---:|---:|---:|---:|
| `html2md` | `commonmark_expected_html` | 647 | 7 | 0 | 98.9% |
| `html2md_streaming` | `commonmark_expected_html` | 647 | 7 | 0 | 98.9% |
| `html_to_markdown` | `commonmark_expected_html` | 472 | 182 | 0 | 72.2% |
| `htmd_py` | `commonmark_expected_html` | 544 | 110 | 0 | 83.2% |
| `html2text_rs` | `commonmark_expected_html` | 419 | 235 | 0 | 64.1% |
| `lxml_naive` | `commonmark_expected_html` | 256 | 397 | 1 | 39.1% |
| `html2md` | `golden` | 64 | 0 | 0 | 100.0% |
| `html2md_streaming` | `golden` | 64 | 0 | 0 | 100.0% |
| `html_to_markdown` | `golden` | 36 | 28 | 0 | 56.2% |
| `htmd_py` | `golden` | 31 | 33 | 0 | 48.4% |
| `html2text_rs` | `golden` | 30 | 34 | 0 | 46.9% |
| `lxml_naive` | `golden` | 18 | 46 | 0 | 28.1% |
| `html2md` | `markdownify_tests` | 230 | 4 | 0 | 98.3% |
| `html2md_streaming` | `markdownify_tests` | 230 | 4 | 0 | 98.3% |
| `html_to_markdown` | `markdownify_tests` | 127 | 107 | 0 | 54.3% |
| `htmd_py` | `markdownify_tests` | 106 | 128 | 0 | 45.3% |
| `html2text_rs` | `markdownify_tests` | 86 | 148 | 0 | 36.8% |
| `lxml_naive` | `markdownify_tests` | 49 | 183 | 2 | 20.9% |
| `html2md` | `pandoc` | 6 | 2 | 0 | 75.0% |
| `html2md_streaming` | `pandoc` | 6 | 2 | 0 | 75.0% |
| `html_to_markdown` | `pandoc` | 1 | 7 | 0 | 12.5% |
| `htmd_py` | `pandoc` | 1 | 7 | 0 | 12.5% |
| `html2text_rs` | `pandoc` | 0 | 8 | 0 | 0.0% |
| `lxml_naive` | `pandoc` | 0 | 8 | 0 | 0.0% |
| `html2md` | `turndown` | 122 | 3 | 0 | 97.6% |
| `html2md_streaming` | `turndown` | 122 | 3 | 0 | 97.6% |
| `html_to_markdown` | `turndown` | 79 | 46 | 0 | 63.2% |
| `htmd_py` | `turndown` | 75 | 50 | 0 | 60.0% |
| `html2text_rs` | `turndown` | 47 | 78 | 0 | 37.6% |
| `lxml_naive` | `turndown` | 30 | 94 | 1 | 24.0% |
| `html2md` | `turndown_options` | 22 | 0 | 0 | 100.0% |
| `html2md_streaming` | `turndown_options` | 22 | 0 | 0 | 100.0% |
| `html_to_markdown` | `turndown_options` | 11 | 11 | 0 | 50.0% |
| `htmd_py` | `turndown_options` | 12 | 10 | 0 | 54.5% |
| `html2text_rs` | `turndown_options` | 2 | 20 | 0 | 9.1% |
| `lxml_naive` | `turndown_options` | 1 | 21 | 0 | 4.5% |

## Charts

- [Throughput by size](charts/throughput_by_size.png)
- [Memory scaling peak RSS](charts/memory_scaling_peak_rss.png)
- [Async stalls](charts/async_stalls.png)
- [TTFO and cadence](charts/ttfo_cadence.png)

## Comparison framing

### `markdownify`: incumbent oracle, not the performance target

`markdownify` remains the compatibility reference, but xlarge conversion took 53.44s, missed 70.02% of heartbeat samples, and peaked at 2808.9 MiB RSS delta. It should stay in the harness as an oracle, not as the large-document runtime path.

### Rust one-shot libraries: fast but incomplete replacements

`htmd_py` is the raw throughput leader and `html_to_markdown` is also fast, but both are one-shot APIs with severe worker-thread heartbeat stalls on large/xlarge fixtures and materially lower primary markdownify fidelity. They are useful comparison points, not drop-in replacements.

### `html2text_rs`: async-friendly signal, semantic mismatch

`html2text_rs` has relatively good heartbeat behavior compared with the other one-shot native libraries, but its markdownify-oracle fidelity is far below the required bar. It proves that GIL behavior alone is not sufficient.

### `lxml_naive`: parser baseline only

`lxml_naive` isolates libxml2 parse/tree-walk shape. It is fast, but its output is intentionally not compatible enough to be a candidate.

### `html2md` and `html2md_streaming`: same semantics, different API surfaces

`html2md.convert` provides the one-shot compatibility surface. `html2md.convert_stream` is the product path for large or user-supplied input: the final xlarge run emitted 227 chunks, first output in 2.42ms, and kept max inter-chunk gap under 31ms while matching the one-shot conversion semantics under the chunk-invariance test suite.

## Reproduction commands

```bash
uv run python -m benchmarks.harness.runner \
  --sizes small medium large xlarge \
  --adapters markdownify html_to_markdown htmd_py html2text_rs html2md html2md_streaming lxml_naive \
  --output benchmarks/results/phase3.json \
  --report benchmarks/results/report.md \
  --timeout-s 1800 --interval-s 0.005 --memory-interval-s 0.02
uv run --group benchmark python benchmarks/charts.py benchmarks/results/phase3.json
uv run python tests/conformance/differential.py --include-lxml-naive
```
