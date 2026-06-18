# Code Review: zo-1fp Makefile + E2E xfail cleanup (R1, reviewer-leaf)

- Bead: zo-1fp (Makefile / CI-target deliverable; no dedicated Makefile bead found)
- Commit range: 5ce0304..20ad459
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 81fffed

## Findings

### P1 - `make all` is not a usable PR gate because its new lint/typecheck targets fail on the current tree

**Location:** `Makefile:33-37`, `Makefile:45`

**Problem**

The new `Makefile` advertises `all` as "Lint + typecheck + the full PR test suite" and wires it to `lint typecheck test conformance property e2e`. But the first two targets fail on the current tracked tree:

- `make lint` (`Makefile:33-34`) runs `uvx ruff check .` and fails with existing E401/E402 diagnostics in `benchmarks/harness/test_fixtures.py:17` and `tests/conformance/differential.py:24-28`.
- `make typecheck` (`Makefile:36-37`) runs `uvx ty check src` and fails with 24 diagnostics in current `src/html2md`, including `src/html2md/_threaded.py:78`, `src/html2md/emitter.py:192`, `src/html2md/emitter.py:346`, `src/html2md/options.py:101`, and `src/html2md/parser.py:21`.

This means `make all` currently stops before running the tests and cannot be used as the claimed PR gate. It also creates an attractive nuisance for future agents: the repo now documents targets that are expected to fail immediately.

**Suggested fix**

Either make the targets pass before advertising them as part of `all`, or scope/name them so their current failure state is explicit. Good options:

1. Fix or configure the existing ruff/ty diagnostics and keep `all: lint typecheck ...`.
2. If typechecking is not yet required, remove `typecheck` from `all` and label it experimental/future, but keep the target available.
3. For lint, either fix the existing diagnostics or use a checked subset that is expected to pass; avoid `ruff check .` in `all` until the whole tree is clean.

---

### P1 - Makefile test/bench targets omit required dependency groups used by the established commands

**Location:** `Makefile:18-28`, `Makefile:39-43`

**Problem**

Several targets are wired as plain `uv run ...` even though the project's established commands for those suites require the `benchmark` dependency group:

- `Makefile:18-19` `conformance` runs `uv run pytest tests/conformance`, but the conformance harness imports benchmark/corpus dependencies such as `markdownify`, `beautifulsoup4`, `markdown-it-py`, and benchmark adapters from the `benchmark` group.
- `Makefile:21-22` `property` runs `uv run pytest tests/property`, but `tests/property/test_metamorphic.py::test_markdown_commonmark_round_trip_is_structurally_stable` uses `markdown-it-py`; without the benchmark group this can skip/under-test the documented xfail relation rather than exercising it.
- `Makefile:39-43` `bench` / `bench-baseline` run the benchmark harness without `--group benchmark`, even though the harness exists specifically to compare third-party benchmark adapters from that group.

This may work in an already-warmed local environment, but a fresh `uv` environment following the Makefile can fail or silently skip coverage.

**Suggested fix**

Mirror the commands we have been validating during the bead reviews:

- `conformance`: `uv run --group benchmark pytest tests/conformance`
- `property`: `uv run --group benchmark pytest tests/property`
- `bench` / `bench-baseline`: `uv run --group benchmark python -m benchmarks.harness.runner ...`

Consider whether `e2e` / `e2e-full` should also opt into any fixture-generation group if those fixtures are regenerated as part of CI, but the current E2E tests themselves passed with the default environment here.

## Positive notes

- The E2E xfail cleanup in `tests/e2e/test_blackbox.py:135-161` is correct: the `small`/`medium` and `xlarge` `convert == convert_stream` checks are now hard assertions, and `make e2e` reports no xfails locally.
- `make help` and `make -n all` print the expected target list / command sequence.

## Tests / checks run

- `make help` → listed all targets
- `make -n all` → printed the expected command sequence
- `make e2e` → 17 passed, 4 skipped in 1.86s
- `make lint` → failed with ruff E401/E402 diagnostics
- `make typecheck` → failed with 24 ty diagnostics

## Summary

2 findings: 0 P0, 2 P1, 0 P2, 0 P3

**Verdict**: Not approved

## Disposition (R1 → R2, coder-2-leaf)

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | P1 | `make lint`/`make typecheck` fail → `make all` not a usable gate | **Fixed** (zo-1fp.20, multi-agent): ruff now green (differential.py E402 → coder-1; benchmarks E401 split → coder-2 @1fe255e); ty now green (options.py 20× → coder-2 @8105d8b; emitter/parser/_threaded → misc @6f7c20f). `make lint` and `make typecheck` both "All checks passed!". |
| 2 | P1 | conformance/property/bench omit `--group benchmark` | **Fixed** @9f6bfdb — those targets now use `uv run --group benchmark`. |

`make all` verified end-to-end: lint ✓ · typecheck ✓ · test ✓ · conformance 93 passed · property 5 passed/1 xfailed · e2e 17 passed/4 skipped.
