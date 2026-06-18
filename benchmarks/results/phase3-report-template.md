# Phase 3 HTML→Markdown final comparison report

> Template status: **draft / unpopulated**. Do not treat placeholder values as results.
> Populate this after phase-2 reaches the fidelity gate (≥99%) and the full phase-3
> matrix writes `benchmarks/results/phase3.json`.

Generated: `TBD`
Fixture manifest: `benchmarks/fixtures.lock.json`
Conformance corpus: `TBD` cases from `tests/conformance/`
Gate version: `v1`

## Executive summary

**Headline:** `marktide` is expected to be the only contender that is simultaneously:

1. **Fast** — competitive warm throughput on large/xlarge fixtures.
2. **Async-friendly** — worker-thread conversion keeps event-loop stalls below the v1 heartbeat gate.
3. **Streaming** — native `marktide.convert_stream` provides measurable TTFO/inter-chunk cadence; one-shot libraries structurally fail this criterion.
4. **Markdownify-faithful** — ≥99% normalized conformance against the markdownify oracle.

Final narrative to fill after the run:

- Winner: `TBD`
- Why it wins: `TBD`
- Largest remaining caveat: `TBD`
- Recommended next action: `TBD`

This report is structured around the decision we actually need to make: whether a
replacement for `markdownify` can preserve markdownify-compatible output while removing
the incumbent's large-document performance, memory, and event-loop failure modes. A
throughput-only winner is insufficient. A semantically faithful but one-shot converter is
also insufficient. The replacement needs to pass all four dimensions at once: fidelity,
throughput, bounded memory behavior, and streaming/async behavior.

The expected final conclusion is that `marktide_streaming` is the only row designed to
satisfy the complete bar. `marktide` shares the same parser/emitter core through the
one-shot API and is useful for API compatibility and simple call sites, but the streaming
row is the decisive product path for large or user-supplied documents.

## Inputs and methodology

### Contenders

| Adapter | API path | Engine | Streaming-capable | Notes |
|---|---|---|---:|---|
| `markdownify` | `markdownify.markdownify(str)` | BeautifulSoup / pure Python | No | Incumbent baseline and oracle reference. |
| `html_to_markdown` | `html_to_markdown.convert(str).content` | Rust via PyO3 | No | High-throughput one-shot candidate. |
| `htmd_py` | `htmd.convert_html(str)` | Rust via PyO3 | No | High-throughput one-shot candidate. |
| `html2text_rs` | `html2text_rs.text_markdown(str)` | Rust via PyO3 | No | GIL/heartbeat-friendly but semantically divergent. |
| `marktide` | `marktide.convert(bytes)` | lxml target parser + Python emitter | No | Local one-shot API row. |
| `marktide_streaming` | `marktide.convert_stream([bytes])` | lxml target parser + Python emitter | Yes | Local streaming API row; only row with TTFO/cadence. |
| `lxml_naive` | harness baseline | libxml2 parse + naive Python walk | No | Performance baseline only, not semantic contender. |

### Performance methodology

- Fixtures: `small`, `medium`, `large`, `xlarge` from `benchmarks/fixtures.lock.json`.
- Each adapter row is warmed with a tiny payload before measuring one full fixture conversion.
- Heartbeat metrics are sampled while the conversion runs in a worker thread.
- Streaming cadence is measured only for adapters exposing a native streaming API.
- RSS uses sampled `resource.getrusage(...).ru_maxrss` while each row conversion is in flight; `memory_curve` records peak delta and per-sample values for the small→xlarge scaling chart.

The performance run intentionally records several overlapping signals instead of a single
"seconds elapsed" number. Wall time and MiB/s answer whether the converter is fast enough
for batch work. Heartbeat missed-beat percentage and max stall answer whether the same
converter is safe to call from an async application via the worker-thread path. TTFO and
inter-chunk cadence answer whether callers can start consuming Markdown before the whole
document is converted. Peak RSS and the small→xlarge memory slope answer whether the
implementation is truly bounded enough for large untrusted inputs.

Interpretation rules:

- A one-shot library gets no streaming credit even if it is fast, because it cannot emit
  early output or demonstrate streaming cadence.
- A library that blocks the event loop in the worker-thread heartbeat probe is unsuitable
  for latency-sensitive async request paths, even if its total wall time is low.
- A library whose RSS scales linearly with input is acceptable only for bounded batch
  workloads; it is not the target architecture for `marktide.convert_stream`.
- `lxml_naive` is included only to show parser/tree-walk performance shape; it is not a
  semantic contender.

### Conformance methodology

- Corpus: `TBD` total cases.
- Oracle(s): markdownify default oracle plus any normalized oracle layers produced by the conformance harness.
- Scoring: `passed / total` and normalized fidelity percentage per library.
- Divergences: link to `tests/conformance/reports/latest.md` or phase-3 conformance report once generated.

The quality score is the gate that prevents a fast parser from becoming a product
regression. `markdownify` is the behavioral contract because existing downstream output
and tests are built around it. Known parser-level differences that cannot be represented
from lxml's recovered SAX stream should be reported separately as allowed divergences;
everything else counts against fidelity until fixed. The final report should call out both
the raw score and the effective score after explicitly allowed parser divergences so the
reader can distinguish implementation bugs from unavoidable parser-recovery differences.

## Performance matrix

Populate from `benchmarks/results/phase3.json`.

The table below is the canonical measured matrix. Use it to answer "how fast" and
"how healthy under async pressure" per fixture. The accompanying charts are easier to
read for trends; this table is the audit trail with exact values.

| Adapter | Fixture | Status | MiB/s | Wall s | Missed beat % | Max stall ms | p99 stall ms | TTFO ms | Max stream gap ms | Stream chunks | Output/Input | Peak RSS Δ MiB | Async pass | Streaming pass |
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
| `marktide` | small | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `marktide` | medium | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `marktide` | large | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `marktide` | xlarge | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `marktide_streaming` | small | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `marktide_streaming` | medium | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `marktide_streaming` | large | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `marktide_streaming` | xlarge | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `lxml_naive` | small | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `lxml_naive` | medium | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `lxml_naive` | large | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |
| `lxml_naive` | xlarge | TBD | TBD | TBD | TBD | TBD | TBD | — | — | — | TBD | TBD | TBD | No |

## Peak RSS / memory scaling

Populate from `memory_scaling` in `benchmarks/results/phase3.json`.

This is the key DSST bounded-memory evidence. The important pattern is not just the
absolute MiB value on one fixture; it is the slope from small to xlarge. One-shot
adapters are expected to rise with input size because they materialize the input/DOM or
full output in memory. The streaming `marktide_streaming` row should be substantially
flatter because the parser/emitter operates over chunks and stack depth instead of the
entire document. If the final data does not show that shape, treat it as a release blocker
for the streaming claim and inspect the largest retained buffers before publishing the
recommendation.

| Adapter | Fixture | Input MiB | Peak RSS Δ MiB | RSS/Input | Samples | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| `markdownify` | small | TBD | TBD | TBD | TBD | Expected O(input) baseline. |
| `markdownify` | medium | TBD | TBD | TBD | TBD | TBD |
| `markdownify` | large | TBD | TBD | TBD | TBD | TBD |
| `markdownify` | xlarge | TBD | TBD | TBD | TBD | TBD |
| `marktide_streaming` | small | TBD | TBD | TBD | TBD | Expected bounded streaming path. |
| `marktide_streaming` | medium | TBD | TBD | TBD | TBD | TBD |
| `marktide_streaming` | large | TBD | TBD | TBD | TBD | TBD |
| `marktide_streaming` | xlarge | TBD | TBD | TBD | TBD | Should stay substantially flatter than one-shot contenders. |

## Gate summary

The gate summary is deliberately strict: an adapter must pass every dimension to be a
true replacement. This prevents a misleading "fastest library wins" narrative. The expected
shape is that some Rust libraries win raw throughput, `html2text_rs` may look good on
heartbeat behavior, and `markdownify` wins only as the incumbent oracle, but only
`marktide_streaming` is expected to combine all required properties.

| Adapter | Throughput pass | Async pass | RSS pass | Streaming TTFO/cadence pass | Conformance pass | Overall |
|---|---|---|---|---|---|---|
| `markdownify` | TBD | TBD | TBD | No | TBD | TBD |
| `html_to_markdown` | TBD | TBD | TBD | No | TBD | TBD |
| `htmd_py` | TBD | TBD | TBD | No | TBD | TBD |
| `html2text_rs` | TBD | TBD | TBD | No | TBD | TBD |
| `marktide` | TBD | TBD | TBD | No | TBD | TBD |
| `marktide_streaming` | TBD | TBD | TBD | TBD | TBD | TBD |
| `lxml_naive` | TBD | TBD | TBD | No | TBD | TBD |

## Conformance / quality matrix

Populate from the phase-3 conformance run.

Use this section to explain semantic risk in plain language. A lower fidelity score should
be paired with examples of the kinds of Markdown differences observed (tables, escaping,
links, whitespace, parser recovery, etc.). For `marktide`, list any remaining allowed
divergences with links to their bead or report entry. For non-selected libraries, the
quality matrix should make clear whether they fail because they are semantically different
by design or because they lack option surfaces to emulate markdownify.

| Adapter | Oracle/layer | Passed | Failed | Total | Fidelity % | Notes |
|---|---|---:|---:|---:|---:|---|
| `markdownify` | markdownify-default | TBD | TBD | TBD | TBD | Oracle self-check. |
| `html_to_markdown` | markdownify-default | TBD | TBD | TBD | TBD | TBD |
| `htmd_py` | markdownify-default | TBD | TBD | TBD | TBD | TBD |
| `html2text_rs` | markdownify-default | TBD | TBD | TBD | TBD | TBD |
| `marktide` | markdownify-default | TBD | TBD | TBD | TBD | Expected ≥99%. |
| `marktide_streaming` | markdownify-default | TBD | TBD | TBD | TBD | Should match `marktide` output hash/fidelity. |
| `lxml_naive` | markdownify-default | TBD | TBD | TBD | TBD | Baseline only. |

## Key charts to generate

- Throughput by fixture size: `adapter × MiB/s`.
- Event-loop health: `adapter × max stall ms` and `adapter × missed beat %`.
- Streaming latency: `marktide_streaming × TTFO/max gap` across sizes.
- Conformance: `adapter × fidelity %`.
- Memory: `adapter × Peak RSS Δ MiB` on large/xlarge.

## Comparison framing

### `markdownify`: incumbent oracle, not the performance target

`markdownify` defines the compatibility target. Its output is the behavior we are trying
to preserve, so it should be treated as the semantic baseline even when it loses on
throughput or async health. The expected final story is that `markdownify` remains useful
as an oracle and migration reference but is not viable for large-document, low-latency, or
streaming use cases.

### Rust one-shot libraries: fast but incomplete replacements

`html_to_markdown` and `htmd_py` are expected to show strong raw throughput. That result
should be acknowledged directly: they are good evidence that native parsing/conversion can
be fast. The comparison point is that phase-3 is not a throughput bake-off alone. These
libraries do not provide the streaming behavior the design requires, and any fidelity gaps
against markdownify mean they cannot serve as drop-in replacements without downstream
output churn.

### `html2text_rs`: async-friendly signal, semantic mismatch

`html2text_rs` may have better heartbeat behavior than other one-shot libraries, but the
phase-1 spot checks and conformance harness identify material markdownify divergence. In
the final prose, use it as the example of why async friendliness alone is not enough.

### `lxml_naive`: parser baseline only

`lxml_naive` exists to isolate the performance shape of libxml2 parsing plus a simplistic
Python walk. It should not be described as a candidate replacement. If it is fast, that
supports the architectural premise that lxml can be a viable substrate; if it is
semantically poor, that is expected.

### `marktide` and `marktide_streaming`: same semantics, different API surfaces

The one-shot `marktide` row demonstrates the compatibility API path. The
`marktide_streaming` row demonstrates the architecture's main advantage: early output,
measurable cadence, and bounded memory shape while preserving the same Markdown output.
The final recommendation should prefer `marktide.convert_stream` for large documents and
keep `marktide.convert` as the convenient small-document/drop-in API.

## Headline narrative draft

1. `markdownify` remains the semantic reference but is slow and event-loop-hostile on large inputs.
2. Rust one-shot libraries are fast, but do not provide native streaming; several also diverge from markdownify semantics.
3. `html2text_rs` is relatively async-friendly but fails the markdownify-fidelity requirement and is still one-shot.
4. `marktide_streaming` is the only expected row that can pass the combined bar: fast enough, async-friendly, native streaming cadence, bounded memory behavior, and ≥99% markdownify fidelity.
5. Therefore, the final recommendation should be: **adopt `marktide` as the replacement, with `marktide.convert_stream` as the preferred large-document API** if phase-3 measurements confirm the expected gate outcomes.

Suggested final summary paragraph once numbers are populated:

> The phase-3 matrix confirms that `marktide_streaming` is the only contender that
> satisfies the full replacement contract. `markdownify` remains the semantic oracle but
> fails the performance/async profile. The Rust candidates demonstrate strong one-shot
> throughput but fail streaming and/or fidelity requirements. `marktide_streaming` combines
> markdownify-compatible output with worker-thread async health, bounded memory scaling,
> and native time-to-first-output. We should adopt `marktide` as the markdownify replacement
> and route large-document call sites to `marktide.convert_stream`.

## Evidence links

- Perf JSON: `benchmarks/results/phase3.json` (TBD)
- Final report: `benchmarks/results/report.md` or this populated template (TBD)
- Conformance report: `tests/conformance/reports/latest.md` (TBD)
- Phase-1 baseline: `benchmarks/results/phase1.json`, `benchmarks/results/report.md`

## Commands to run for the final report

Fill in exact command output after the ≥99% go-signal. Expected sequence:

```bash
uv run python -m benchmarks.harness.runner \
  --sizes small medium large xlarge \
  --adapters markdownify html_to_markdown htmd_py html2text_rs marktide marktide_streaming lxml_naive \
  --output benchmarks/results/phase3.json \
  --report benchmarks/results/report.md

uv run --group benchmark python benchmarks/charts.py benchmarks/results/phase3.json

# Then run the conformance command owned by tests/conformance and copy its summary here.
```

## Open follow-ups after final run

- Replace all `TBD` placeholders with measured values.
- Verify `marktide` and `marktide_streaming` output hashes match for every fixture.
- Include any known remaining fidelity divergences and their bead IDs.
- Include exact commands used to generate `phase3.json`, charts, and conformance results.
- Replace the suggested summary paragraph with measured numbers and chart links.
