# marktide benchmarks

This directory is a **self-contained uv project** for reproducing the
HTML→Markdown comparison numbers. It has its own `pyproject.toml` and
`uv.lock`; the benchmark project depends on the parent checkout via an editable
path dependency on `marktide`.

## One-command verification

From this directory:

```bash
uv sync
uv run bench
```

`uv run bench` is the skeptic-friendly quick verification. It runs the small and
medium fixtures across all seven contenders:

- `markdownify`
- `html_to_markdown`
- `htmd_py`
- `html2text_rs`
- `marktide`
- `marktide_streaming`
- `lxml_naive`

At the end, it prints the async-loop-starvation proof in a dedicated block. The
expected headline on the medium fixture is:

```text
=== ASYNC-LOOP STARVATION PROOF (benchmark harness heartbeat) ===
markdownify        medium : missed≈70% ...
marktide_streaming  medium : missed=0.00% ... TTFO≈2-4ms
```

That heartbeat / async-starvation measurement lives in
`benchmarks/harness/probe.py`. It is a **benchmark harness measurement**, not an
e2e test-suite assertion.

The quick run writes:

- `results/verify.json`
- `results/verify.md`

## Full phase-3 matrix

To run the full small→xlarge matrix and regenerate charts:

```bash
uv run bench --full
```

This runs all seven contenders on `small`, `medium`, `large`, and `xlarge`, then
writes:

- `results/phase3-repro.json`
- `results/phase3-repro.md`
- `results/charts/throughput_by_size.png`
- `results/charts/memory_scaling_peak_rss.png`
- `results/charts/async_stalls.png`
- `results/charts/ttfo_cadence.png`

The xlarge `markdownify` row is intentionally slow (about 50 seconds on the
reference machine), so the full run takes materially longer than `uv run bench`.

To overwrite the committed canonical report artifacts explicitly:

```bash
uv run bench --full --output results/phase3.json --report results/report.md
```

## Async-starvation-only proof

For the smallest possible reproduction of the headline async claim:

```bash
uv run bench-async-starvation
```

This runs only `markdownify` and `marktide_streaming` on the medium fixture and
prints missed heartbeat percentage, max stall, p99 stall, and streaming TTFO.

To test a different fixture:

```bash
uv run bench-async-starvation --fixture large
```

## Direct harness commands

The script entrypoints above call the same harness used for the committed
phase-1 and phase-3 results. If you need direct control:

```bash
uv run python -m harness.runner \
  --sizes small medium large xlarge \
  --adapters markdownify html_to_markdown htmd_py html2text_rs marktide marktide_streaming lxml_naive \
  --output results/phase3-repro.json \
  --report results/phase3-repro.md \
  --timeout-s 1800 \
  --interval-s 0.005 \
  --memory-interval-s 0.02

uv run python charts.py results/phase3-repro.json
```

## Reproducibility notes

- `uv.lock` is committed for deterministic dependency resolution.
- `html-to-markdown` is pinned at `3.5.7`.
- `marktide` is an editable path dependency on the parent directory (`..`), so the
  benchmark always measures the local checkout.
- Fixture hashes are checked against `fixtures.lock.json` before every run.
- `results/*.json` is ignored by the root `.gitignore`; force-add any new
  canonical JSON result intentionally.
