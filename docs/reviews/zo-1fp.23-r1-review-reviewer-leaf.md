# Code Review: zo-1fp.23 (R1, reviewer-leaf)

- Bead: zo-1fp.23
- Commit range: 3571715
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 3571715

## Findings

No findings.

## Positive notes

- `Makefile:24-25` exposes `make verify-fidelity` as the requested one-command verifier from the repository root.
- `tests/conformance/verify_fidelity.py:98-179` recomputes the layered differential corpus rather than reading stale committed report JSON, prints the primary raw/effective headline for both `html2md` and `html2md_streaming`, prints per-oracle guardrail totals, and fails on primary unallowed failures, primary candidate errors, or any one-shot/streaming parity mismatch.
- `tests/conformance/README.md:68-90` documents the command, the exact current primary fidelity claim (`296/298` raw, `298/298` effective), the `golden` and corrected `markdownify_tests` components, and the non-primary guardrail oracles.

## Checks run

- `make verify-fidelity`
- `uv run ruff check tests/conformance/verify_fidelity.py`
- `uvx ty check tests/conformance/verify_fidelity.py`
- Inspected `Makefile:24-25`, `tests/conformance/README.md:68-90`, and `tests/conformance/verify_fidelity.py:98-179` against the bead requirement.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
