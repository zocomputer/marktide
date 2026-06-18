# Code Review: zo-1fp docs deliverable (R2, reviewer-leaf)

- Bead: zo-1fp (docs deliverable; no dedicated docs bead found)
- Commit range: 59ea552..b74bc62
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: b74bc62

## Findings

No findings.

## Verification

R1 findings were incorporated:

1. `README.md:3-6`, `README.md:40-42`, and `README.md:92-95` now scope the project as a near drop-in / markdownify-compatible implementation with documented divergences, rather than promising identical output everywhere.
2. `docs/usage.md:170-208` now scopes migration compatibility, documents that conformance is high but not yet 100%, names intentional divergences, and calls remaining CDATA/whitespace gaps open conformance work.
3. `README.md:34-37` and `docs/usage.md:225-227` now describe the memory bound as no full DOM plus parser open-element state and the largest currently-open block/table, which matches the emitter buffering model.
4. `docs/reviews/zo-1fp-docs-r1-review-reviewer-leaf.md` includes the R1 disposition table.

## Checks run

- Re-verified the committed README / usage code examples against the live API with `uv run python`.
- Reviewed the wording diff in `README.md`, `docs/usage.md`, and the R1 disposition table.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
