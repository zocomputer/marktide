# Code Review: zo-1fp Makefile + E2E xfail cleanup (R2, reviewer-leaf)

- Bead: zo-1fp (Makefile / CI-target deliverable; no dedicated Makefile bead found)
- Related bead: zo-1fp.20
- Commit range: 56b9ed9..b73d55f
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: b73d55f

## Findings

No findings.

## Verification

R1 findings were incorporated:

1. `Makefile:33-37` / `Makefile:45` now form a usable `make all` gate because `make lint` and `make typecheck` pass on the current tree.
2. `Makefile:18-28` and `Makefile:39-43` now use `uv run --group benchmark` for `conformance`, `property`, `bench`, and `bench-baseline`, matching the dependency groups those suites/harnesses require.
3. `docs/reviews/zo-1fp-makefile-r1-review-reviewer-leaf.md` includes the R1 disposition table.
4. The E2E xfail removal remains correct: `tests/e2e/test_blackbox.py:135-161` enforces real `convert == convert_stream` checks for `small`, `medium`, and nightly `xlarge` without xfail markers.

## Tests / checks run

- `make all` → passed end-to-end:
  - `uvx ruff check .` → passed
  - `uvx ty check src` → passed
  - `uv run pytest tests/unit tests/component` → 1370 passed
  - `uv run --group benchmark pytest tests/conformance` → 93 passed
  - `uv run --group benchmark pytest tests/property` → 5 passed, 1 xfailed
  - `uv run pytest tests/e2e` → 17 passed, 4 skipped
- `make -n conformance property bench bench-baseline` → all four commands include `--group benchmark`

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
