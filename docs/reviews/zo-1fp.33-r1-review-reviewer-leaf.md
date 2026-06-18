# Code Review: zo-1fp.33 (R1, reviewer-leaf)

- Bead: zo-1fp.33
- Commit range: 1a12281
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 1a12281

## Findings

No findings.

## Positive notes

- `README.md:3-9` now surfaces both sync and async Python usage in the opening paragraph, as requested.
- The async claim is consistent with `README.md:70-95` and the implementation: async entry points route conversion work off the event loop via `asyncio.to_thread`, while sync APIs are reserved for non-async contexts.
- The wording remains concise and preserves the existing lxml / markdownify-compatible framing.

## Checks run

- Reviewed `README.md:1-15` against the previously approved `README.md:70-95` production guidance and public API descriptions.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
