# Code Review: zo-1fp.27 (R2, reviewer-leaf)

- Bead: zo-1fp.27
- Commit range: 1eb9a8f
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 1eb9a8f

## Findings

### P1 - The integrated `make test` gate is still not green at the review commit

**Location:** `Makefile:18-19`, `tests/property/test_metamorphic.py:190-200`

**Problem**

The original R1 fixtureless collection blocker in `tests/component/test_chunk_invariance.py` is fixed by `1eb9a8f`: `tests/component/test_chunk_invariance.py:176-190` now returns a sentinel `Case` and skips inside the test body, and the targeted component suite passes.

However, `zo-1fp.27` is specifically the bead that makes `make test` the full CI gate. At the current integrated review commit, `make test` is still not green because the property suite introduced by the same commit fails. The failing command is:

```text
uv run --group benchmark pytest tests/property -q
```

with minimized input `'<p><code>0 </code><code> 0</code></p>'` in `tests/property/test_metamorphic.py:190-200`. Details are tracked in `docs/reviews/zo-1fp.28-r1-review-reviewer-leaf.md`.

This is not the same fixtureless-skip issue from R1, but it still blocks approving the `make test` full-gate claim for the current branch state.

**Suggested fix**

Fix the `zo-1fp.28` property failure, then rerun the full `make test` gate. Once `make test` is green, this bead can be approved.

## Positive notes

- The R1 fixtureless collection issue is addressed in `tests/component/test_chunk_invariance.py:176-190`.
- `make lint` passed.
- `uv run --group benchmark pytest tests/component/test_chunk_invariance.py -q` passed with `1124 passed` in the fixture-present checkout.

## Checks run

- `make lint` — passed.
- `make verify-fidelity` — passed.
- `make conformance` — passed.
- `uv run --group benchmark pytest tests/component/test_chunk_invariance.py -q` — passed.
- `uv run --group benchmark pytest tests/property -q` — failed; therefore `make test` is not green at this integrated commit.

## Summary

1 finding: 0 P0, 1 P1, 0 P2, 0 P3

**Verdict**: Not approved
