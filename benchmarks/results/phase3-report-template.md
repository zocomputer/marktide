# Phase 3 HTML→Markdown final comparison report

> Template status: **draft / unpopulated**. Do not treat placeholder values as results.
> Populate this after phase-2 reaches the fidelity gate (≥99%) and the full phase-3
> matrix writes `benchmarks/results/phase3.json`.

Generated: `TBD`
Fixture manifest: `benchmarks/fixtures.lock.json`
Conformance corpus: `TBD` cases from `tests/conformance/`
Gate version: `v1`

## Executive summary

**Headline:** `html2md` is expected to be the only contender that is simultaneously:

1. **Fast** — competitive warm throughput on large/xlarge fixtures.
2. **Async-friendly** — worker-thread conversion keeps event-loop stalls below the v1 heartbeat gate.
3. **Streaming** — native `html2md.convert_stream` provides measurable TTFO/inter-chunk cadence; one-shot libraries structurally fail this criterion.
4. **Markdownify-faithful** — ≥99% normalized conformance against the markdownify oracle.

Final narrative to fill after the run:

- Winner: `TBD`
- Why it wins: `TBD`
- Largest remaining caveat: `TBD`
- Recommended next action: `TBD`

## Inputs and methodology

### Contenders

| Adapter | API path | Engine | Streaming-capable | Notes |
|---|---|---|---:|---|
| `markdownify` | `markdownify.markdownify(str)` | BeautifulSoup / pure Python | No | Incumbent baseline and oracle reference. |
| `html_to_markdown` | `html_to_markdown.convert(str).content` | Rust via PyO3 | No | High-throughput one-shot candidate. |
| `htmd_py` | `htmd.convert_html(str)` | Rust via PyO3 | No | High-throughput one-shot candidate. |
| `html2text_rs` | `html2text_rs.text_markdown(str)` | Rust via PyO3 | No | GIL/heartbeat-friendly but semantically divergent. |
| `html2md` | `html2md.convert(bytes)` | lxml target parser + Python emitter | No | Local one-shot API row. |
| `html2md_streaming` | `html2md.convert_stream([bytes])` | lxml target parser + Python emitter | Yes | Local streaming API row; only row with TTFO/cadence. |
| `lxml_naive` | harness baseline | libxml2 parse + naive Python walk | No | Performance baseline only, not semantic contender. |

### Performance methodology

- Fixtures: `small`, `medium`, `large`, `xlarge` from `benchmarks/fixtures.lock.json`.
- Each adapter row is warmed with a tiny payload before measuring one full fixture conversion.
- Heartbeat metrics are sampled while the conversion runs in a worker thread.
- Streaming cadence is measured only for adapters exposing a native streaming API.
- RSS uses `resource.getrusage(...).ru_maxrss` deltas from each row subprocess.

### Conformance methodology

- Corpus: `TBD` total cases.
- Oracle(s): markdownify default oracle plus any normalized oracle layers produced by the conformance harness.
- Scoring: `passed / total` and normalized fidelity percentage per library.
- Divergences: link to `tests/conformance/reports/latest.md` or phase-3 conformance report once generated.

## Performance matrix

Populate from `benchmarks/results/phase3.json`.

| Adapter | Fixture | Status | MiB/s | Wall s | Missed beat % | Max stall ms | p99 stall ms | TTFO ms | Max stream gap ms | Stream chunks | Output/Input | RSS delta MiB | Async pass | Streaming pass |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `markdownify` | small | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `markdownify` | medium | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `markdownify` | large | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `markdownify` | xlarge | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html_to_markdown` | small | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html_to_markdown` | medium | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html_to_markdown` | large | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html_to_markdown` | xlarge | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `htmd_py` | small | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `htmd_py` | medium | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `htmd_py` | large | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `htmd_py` | xlarge | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html2text_rs` | small | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html2text_rs` | medium | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html2text_rs` | large | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html2text_rs` | xlarge | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html2md` | small | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html2md` | medium | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html2md` | large | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html2md` | xlarge | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `html2md_streaming` | small | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `html2md_streaming` | medium | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `html2md_streaming` | large | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `html2md_streaming` | xlarge | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `lxml_naive` | small | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `lxml_naive` | medium | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `lxml_naive` | large | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `lxml_naive` | xlarge | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |

## Gate summary

| Adapter | Throughput pass | Async pass | RSS pass | Streaming TTFO/cadence pass | Conformance pass | Overall |
|---|---|---|---|---|---|---|
| `markdownify` | TBD | TBD | TBD | No | TBD | TBD |
| `html_to_markdown` | TBD | TBD | TBD | No | TBD | TBD |
| `htmd_py` | TBD | TBD | TBD | No | TBD | TBD |
| `html2text_rs` | TBD | TBD | TBD | No | TBD | TBD |
| `html2md` | TBD | TBD | TBD | No | TBD | TBD |
| `html2md_streaming` | TBD | TBD | TBD | TBD | TBD | TBD |
| `lxml_naive` | TBD | TBD | TBD | No | TBD | TBD |

## Conformance / quality matrix

Populate from the phase-3 conformance run.

| Adapter | Oracle/layer | Passed | Failed | Total | Fidelity % | Notes |
|---|---|---:|---:|---:|---:|---|
| `markdownify` | markdownify-default | TBD | TBD | TBD | TBD | Oracle self-check. |
| `html_to_markdown` | markdownify-default | TBD | TBD | TBD | TBD | TBD |
| `htmd_py` | markdownify-default | TBD | TBD | TBD | TBD | TBD |
| `html2text_rs` | markdownify-default | TBD | TBD | TBD | TBD | TBD |
| `html2md` | markdownify-default | TBD | TBD | TBD | TBD | Expected ≥99%. |
| `html2md_streaming` | markdownify-default | TBD | TBD | TBD | TBD | Should match `html2md` output hash/fidelity. |
| `lxml_naive` | markdownify-default | TBD | TBD | TBD | TBD | Baseline only. |

## Key charts to generate

- Throughput by fixture size: `adapter × MiB/s`.
- Event-loop health: `adapter × max stall ms` and `adapter × missed beat %`.
- Streaming latency: `html2md_streaming × TTFO/max gap` across sizes.
- Conformance: `adapter × fidelity %`.
- Memory: `adapter × RSS delta MiB` on large/xlarge.

## Headline narrative draft

1. `markdownify` remains the semantic reference but is slow and event-loop-hostile on large inputs.
2. Rust one-shot libraries are fast, but do not provide native streaming; several also diverge from markdownify semantics.
3. `html2text_rs` is relatively async-friendly but fails the markdownify-fidelity requirement and is still one-shot.
4. `html2md_streaming` is the only expected row that can pass the combined bar: fast enough, async-friendly, native streaming cadence, bounded memory behavior, and ≥99% markdownify fidelity.
5. Therefore, the final recommendation should be: **adopt `html2md` as the replacement, with `html2md.convert_stream` as the preferred large-document API** if phase-3 measurements confirm the expected gate outcomes.

## Evidence links

- Perf JSON: `benchmarks/results/phase3.json` (TBD)
- Final report: `benchmarks/results/report.md` or this populated template (TBD)
- Conformance report: `tests/conformance/reports/latest.md` (TBD)
- Phase-1 baseline: `benchmarks/results/phase1.json`, `benchmarks/results/report.md`

## Open follow-ups after final run

- Replace all `TBD` placeholders with measured values.
- Verify `html2md` and `html2md_streaming` output hashes match for every fixture.
- Include any known remaining fidelity divergences and their bead IDs.
- Include exact commands used to generate `phase3.json` and conformance results.
