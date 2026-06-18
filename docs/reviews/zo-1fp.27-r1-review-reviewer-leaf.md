# Code Review: zo-1fp.27 (R1, reviewer-leaf)

- Bead: zo-1fp.27
- Commit range: a219b3e
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: a219b3e

## Findings

### P1 - `make test` fails in a clean checkout with no generated fixtures

**Location:** `Makefile:18-19`, `tests/component/test_chunk_invariance.py:174-177`

**Problem**

The bead requirement and the new Makefile header say `make test` is runnable with nothing gitignored present. In a detached clean worktree at `a219b3e` with no generated `tests/conformance/fixtures/` directory, `make test` fails during collection before running the suite:

```text
ERROR collecting tests/component/test_chunk_invariance.py
Using pytest.skip outside of a test will skip the entire module. If that's your intention, pass `allow_module_level=True`.
```

The failure comes from `tests/component/test_chunk_invariance.py:174-177`: `conformance_cases()` calls `pytest.skip("conformance fixtures are not generated; ...")` while building the `@pytest.mark.parametrize("case", conformance_cases(), ...)` argument at module import/collection time. Pytest treats that as an error unless the skip is explicitly module-level. This means the simplified CI gate is not actually green for a fresh checkout without gitignored fixtures, despite `Makefile:4-6` documenting that it should be.

**Suggested fix**

Make the component skip collection-safe. For example:

```python
pytest.skip(
    "conformance fixtures are not generated; run scripts/regenerate_conformance_corpus.py",
    allow_module_level=True,
)
```

Alternatively, return a small synthetic case list when fixtures are absent if this test should retain signal in a fixtureless checkout. Then rerun `make test` from a clean checkout/worktree without generated fixture directories.

## Positive notes

- `Makefile:13-42` has the requested shape: `make lint` runs ruff + ty, `make test` runs unit/component/conformance/property/e2e, subset targets keep the bare names, and `make help` is grouped.
- `tests/e2e/conftest.py` is deleted and `tests/e2e/test_blackbox.py:140-160` no longer has `@pytest.mark.nightly`, so the E2E nightly tier is removed.
- `make help` and `make lint` passed in the clean detached worktree at `a219b3e`.

## Checks run

- In the main worktree, `make help` passed and `make lint` passed, but `make test` was confounded by unrelated uncommitted changes in `src/html2md/options.py`, `src/html2md/rules/inline.py`, `tests/property/test_metamorphic.py`, `tests/unit/html2md/test_block_inline_handlers.py`, and `tests/unit/html2md/test_options.py`.
- Created a detached clean worktree at `/Users/dcosson/h2home/worktrees/reviewer-leaf-zo-1fp27` pinned to `a219b3e` and ran:
  - `make lint` — passed.
  - `make test` — failed during `tests/component/test_chunk_invariance.py` collection as described above.
  - `uv run --group benchmark pytest tests/conformance -q` — passed with `10 passed`, confirming the first clean-checkout blocker is the component module-level skip path.

## Summary

1 finding: 0 P0, 1 P1, 0 P2, 0 P3

**Verdict**: Not approved
