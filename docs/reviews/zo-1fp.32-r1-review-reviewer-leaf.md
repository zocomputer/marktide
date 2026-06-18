# Code Review: zo-1fp.32 (R1, reviewer-leaf)

- Bead: zo-1fp.32
- Commit range: 9e3a829
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 9e3a829

## Findings

### P1 - Production warning omits synchronous `convert_stream()` on the event loop

**Location:** `README.md:70-94`, `src/html2md/convert.py:39-58`

**Problem**

The bead asks the README to reserve synchronous `convert()` / `convert_stream()` for non-async contexts. The new production section correctly tells async users to prefer `convert_stream_async()` / `convert_async()` and warns not to call synchronous `convert()` on the event loop for large input, but it never gives the same explicit warning for synchronous `convert_stream()`.

`src/html2md/convert.py:39-58` shows `convert_stream()` is also synchronous: each iteration runs `driver.feed()` and `driver.drain()` on the caller's thread. If a caller iterates `convert_stream()` inside an async handler, the event loop still runs parser/emitter work on its own thread for each chunk. That may be shorter than one-shot `convert()`, but it is still the sync API and should not be the recommended streaming choice in async code.

Because the section is production guidance, leaving `convert_stream()` out of the warning can lead readers to think sync streaming is safe in async code as long as they avoid `convert()`.

**Suggested fix**

Change `README.md:86-90` to warn against both sync APIs in async code. For example: `Do not call synchronous convert() or iterate synchronous convert_stream() on the event loop for large input... Reserve convert() and convert_stream() for non-async contexts.` Keep the rest of the section unchanged.

## Positive notes

- `README.md:70-84` is placed directly below the four public functions as requested and clearly recommends `convert_stream_async()` for unknown/large async input and `convert_async()` for simpler whole-string async conversion.
- `README.md:72-83` matches the implementation: `src/html2md/convert.py:34-36` uses `asyncio.to_thread()` for `convert_async()`, and `src/html2md/_threaded.py:53-70` uses `asyncio.to_thread()` for async streaming feed/drain/close.
- `README.md:86-94` correctly explains that running sync conversion on the loop's own thread blocks the loop, and that GIL release helps other threads rather than the current loop thread.

## Checks run

- Reviewed `README.md:44-94` against `src/html2md/convert.py:22-70` and `src/html2md/_threaded.py:1-76`.

## Summary

1 finding: 0 P0, 1 P1, 0 P2, 0 P3

**Verdict**: Not approved
