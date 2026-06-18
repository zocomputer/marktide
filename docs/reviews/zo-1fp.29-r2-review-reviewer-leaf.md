# Code Review: zo-1fp.29 (R2, reviewer-leaf)

- Bead: zo-1fp.29
- Commit range: 1555e22
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 1555e22

## Findings

No findings.

## R1 disposition verification

- R1 P1 (`README.md:145-146` overclaimed that every listed edge case is tracked in `tests/conformance/allowed_divergences.toml` / surfaced by `make verify-fidelity`): resolved. `README.md:147-151` now scopes that claim to the two primary `<h1>` parser divergences plus the CDATA case, and explicitly says the `<strike>` / `<h7>` / whitespace-span rows are guardrail-layer convention differences not in that ledger.
- R1 P2 (`README.md:122-124` said each differing case was shown and all were invalid/ambiguous HTML): resolved. `README.md:122-126` now says the section is a representative selection, not exhaustive, and distinguishes invalid HTML from convention/whitespace-normalization choices on valid HTML.

## Positive notes

- `README.md:128-145` and `docs/usage.md:199-208` now use the corrected parser framing: lxml/libxml2 is the non-HTML5 side for nested block-in-heading, while lxml is HTML5-correct for the CDATA/bogus-comment case.
- The concrete README examples still match the live converter outputs verified during R1.
- The `07cf2ce` Makefile-target documentation cleanup remains accurate: it points `docs/design.md` at the shipped `make lint`, `make test`, `make unit`, `make conformance`, `make cov`, `make bench`, and `make verify-fidelity` targets, and marks older `docs/test-plan.md` target names as pre-implementation illustrative names.

## Checks run

- Reviewed `README.md:86-159` and `docs/usage.md:195-215` against `tests/conformance/allowed_divergences.toml`, `tests/conformance/reports/latest.json`, and prior live converter checks from R1.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
