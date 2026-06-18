# Code Review: zo-1fp.23 (R1, reviewer-leaf)

- Bead: zo-1fp.23
- Commit range: 3571715
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 3571715

## Findings

### P1 - `make verify-fidelity` mutates the committed conformance reports

**Location:** `tests/conformance/verify_fidelity.py:101-103`, `tests/conformance/reports/latest.json`, `tests/conformance/reports/latest.md`

**Problem**

Running the requested one-command verifier from a clean checkout rewrites `tests/conformance/reports/latest.json` and `tests/conformance/reports/latest.md`. The diff removes the committed `lxml_naive` adapter results from the report artifacts because `tests/conformance/verify_fidelity.py:101-103` calls `get_adapters(include_lxml_naive=False)` and then `run_differential(cases, adapters, max_diff_chars=300)` through the same code path that writes the canonical `latest.*` reports.

This makes `make verify-fidelity` unsafe as a documentation/claim-verification command: a reader trying to verify the README fidelity claim ends with a dirty worktree and accidentally rewrites the official conformance report snapshot with a narrower adapter set.

**Suggested fix**

Add a non-mutating path for the verifier. For example, teach the differential runner to support `write_reports=False` / output path override, or have `tests/conformance/verify_fidelity.py` call lower-level comparison functions that return `CaseResult` values without touching `tests/conformance/reports/latest.json` or `tests/conformance/reports/latest.md`. Add a regression test that runs the verifier and asserts the committed report files are byte-for-byte unchanged.

## Positive notes

- `Makefile:24-25` exposes `make verify-fidelity` as the requested one-command verifier from the repository root.
- The printed fidelity numbers are correct in the current run: primary `296/298` raw and `298/298` effective for both `html2md` and `html2md_streaming`, `golden` `64/64`, corrected `markdownify_tests` `232/234` raw and `234/234` effective, and streaming parity `0/1107`.
- `tests/conformance/README.md:68-90` documents the command, the exact current primary fidelity claim, the `golden` and corrected `markdownify_tests` components, and the non-primary guardrail oracles.

## Checks run

- `make verify-fidelity` — passed, but dirtied `tests/conformance/reports/latest.json` and `tests/conformance/reports/latest.md`.
- `uv run ruff check tests/conformance/verify_fidelity.py`
- `uvx ty check tests/conformance/verify_fidelity.py`
- Inspected `Makefile:24-25`, `tests/conformance/README.md:68-90`, and `tests/conformance/verify_fidelity.py:98-179` against the bead requirement.

## Summary

1 finding: 0 P0, 1 P1, 0 P2, 0 P3

**Verdict**: Not approved
