# Marktide v1.1 changelog

Comparison range: `v1.0-baseline..v1.1`

`v1.1` is a performance and project-readiness release. It keeps the v1.0 public API and markdownify-compatible output contract, while making the emitter faster, refreshing the published benchmark numbers, and making the test suite runnable in a clean GitHub Actions checkout.

## Highlights

- **Faster conversion on large documents.** On the `xlarge` benchmark fixture (~110 MiB), `marktide` streaming now converts in **4.73 s**, compared with **54.55 s** for `markdownify` — **11.5× faster**.
- **Low memory remains intact.** On the same fixture, `marktide` streaming peak RSS growth is **247.3 MiB**, compared with **2811.1 MiB** for `markdownify` — **11.4× lower**.
- **Streaming responsiveness remains strong.** Time-to-first-chunk is now **2.2 ms** on the `xlarge` fixture, with `0.0%` missed event-loop beats in the benchmark run.
- **Fidelity is unchanged.** The primary drop-in oracle remains **298/298 effective** (`296/298` raw), with **0/1107** `marktide` vs `marktide_streaming` mismatches.
- **CI now runs the full gate.** GitHub Actions runs `make lint` and `make test` on every push and pull request.

## Performance changes

- Replaced the per-text-node noformat stack scan with an O(1) `EmitterState.noformat_depth` counter.
- Cached the current output buffer target in `MarkdownEmitter._buf_target`, avoiding repeated open-stack scans in hot paths.
- Added fast paths around whitespace normalization and newline-boundary splitting so clean text skips regex work.
- Added a v2 emission profile artifact and findings document to explain where the Tier-1 optimizations came from.

## Benchmark and documentation updates

- Refreshed `benchmarks/results/phase3.json`, `benchmarks/results/report.md`, and benchmark charts after the Tier-1 optimization pass.
- Updated README benchmark prose and tables to match the refreshed benchmark run.
- Clarified that `htmd_py` and `html2text_rs` are faster in raw wall time, while `html_to_markdown` is roughly tied with `marktide` but still stalls the event loop.
- Added review audit documents for the performance, benchmark, and CI changes.

## Test and CI changes

- Added `.github/workflows/ci.yml` with a minimal `ubuntu-latest` lint-and-test gate:
  - checkout
  - `astral-sh/setup-uv@v5` with Python 3.12
  - `uv sync --group benchmark`
  - `make lint`
  - `make test`
- Vendored the conformance fixture corpora under `tests/conformance/fixtures/` so clean checkouts run the same fixture-backed tests as local development.
- Added `tests/conformance/fixtures/README.md` and updated `tests/conformance/sources.toml` with fixture provenance. The markdownify fixture corpus is copied from `matthewwithanm/python-markdownify` commit `add391a6235cbc66af30ec0202cb00cb0ff0eb4c`; the live runtime oracle dependency remains controlled separately by `pyproject.toml` / `uv.lock`.

## Maintenance

- Removed the local `.beads` symlink from the published repository.
- Kept benchmark/nightly workloads out of the CI gate; CI runs only the primary lint + full test suite.

## Commits included

- `f312c57` — `perf(profile): v2 stage profile of marktide emission overhead (zo-q2m.1)`
- `c52c57e` — `perf(emitter): O(1) noformat depth counter (zo-q2m.2 Tier-1 #1)`
- `53fc88d` — `perf(emitter): cache the buffer-target pointer (zo-q2m.2 Tier-1 #2)`
- `838c981` — `perf(emitter): fast-path the whitespace + newline-split regexes (zo-q2m.2 Tier-1 #3)`
- `0870277` — `benchmarks: refresh phase 3 matrix after tier 1`
- `0ea3e4d` — `docs(readme): update benchmark numbers to the Tier-1 re-run (zo-q2m.3)`
- `d704d92` — `docs(readme): qualify which Rust one-shots are faster (zo-q2m.3 R1)`
- `e284552` — `ci: add GitHub Actions lint + test gate (zo-fp4)`
- `9523dd7` — `test: vendor conformance fixtures for CI`
- `583ecb3` — `remove beads symlink`

Review-only commits in the range add audit trail documents and do not change runtime behavior.
