# Code Review: zo-1fp.15 (R2, reviewer-leaf)

- Bead: zo-1fp.15
- Commit range: 4acc217..fe976f0
- Plan doc: docs/design.md §11
- Reviewer: reviewer-leaf
- Review commit: 121c860

## Findings

No findings.

## Verification

R1 findings were incorporated:

1. `tests/unit/html2md/test_memory_invariant.py:30-42` now includes `MarkdownEmitter.root` in `register_footprint`, so the streamed-root register is measured while it contains committed-but-not-yet-drained output.
2. `tests/unit/html2md/test_memory_invariant.py:49-60` now samples the live footprint after each `driver.feed(...)` and before `driver.drain()`, so root accumulation is observable instead of hidden by the drain.
3. `tests/unit/html2md/test_memory_invariant.py:81-96` adds `test_drain_releases_the_root_register`, proving `drain()` releases the root register and leaves only a tiny unstable trailing region.
4. `tests/unit/html2md/test_memory_invariant.py:99-117` adds both an always-run multi-MB representative large-input validation and a skip-if-absent xlarge fixture-backed validation. On this machine the xlarge fixture is present and the fixture test passed.

## Tests / checks run

- `uv run pytest tests/unit/html2md/test_memory_invariant.py -vv` → 9 passed in 6.71s
- `uv run ruff check tests/unit/html2md/test_memory_invariant.py` → passed
- `make test` → 1370 passed in 7.67s

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
