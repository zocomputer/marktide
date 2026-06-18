# Code Review: zo-1fp.32 (R2, reviewer-leaf)

- Bead: zo-1fp.32
- Commit range: a9979a4
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: a9979a4

## Findings

No findings.

## R1 disposition verification

- R1 P1 (production guidance warned about sync `convert()` but omitted sync `convert_stream()`): resolved. `README.md:86-91` now warns against both synchronous APIs on the event loop, explains that `convert()` blocks for the whole conversion while `convert_stream()` blocks per chunk's feed-and-emit, and reserves both sync APIs for non-async contexts.

## Positive notes

- `README.md:70-95` now matches the implementation in `src/html2md/convert.py`: async code should use `convert_async()` / `convert_stream_async()`, while synchronous APIs are for scripts/workers/sync handlers.
- The section still preserves the useful size-branching guidance: `asyncio.to_thread` dispatch is cheap, so async code can consistently route through async entry points.

## Checks run

- Reviewed `README.md:70-95` against `src/html2md/convert.py:22-70` and `src/html2md/_threaded.py:1-76`.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
