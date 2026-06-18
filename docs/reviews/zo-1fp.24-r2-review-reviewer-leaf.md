# Code Review: zo-1fp.24 (R2, reviewer-leaf)

- Bead: zo-1fp.24
- Commit range: 1009703
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 1009703

## Findings

No findings.

## R1 disposition verification

- R1 P1 (guardrail semantic-comparison overclaim): resolved. `README.md:99-104` now says guardrail inputs are compared to the markdownify oracle after normalization, and specifically scopes rendered-HTML semantic comparison to the CommonMark layer. That matches `tests/conformance/differential.py:416-446`.
- R1 P2 (all corpora described as upstream-pinned): resolved. `README.md:106-109` now says external corpora are upstream-pinned in `tests/conformance/sources.toml`, while the 64-case golden set is hand-authored under `tests/conformance/golden/`.

## Positive notes

- The counts remain correct in `README.md:91-100`: `markdownify_tests` `234` + `golden` `64` = `298` primary cases; Turndown `147` + CommonMark `654` + Pandoc `8` = `809` guardrail cases; total `1107`.
- The reproduction commands at `README.md:111-113` remain valid: `make verify-fidelity` for the primary headline and `make conformance` for the full suite.

## Checks run

- Reviewed `README.md:86-118` against `tests/conformance/differential.py:416-446`, `tests/conformance/sources.toml`, and `tests/conformance/golden/*.json`.
- Reused R1 verification for counts and commands: `make verify-fidelity`, `make conformance`, and `load_cases()` count check.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
