# Code Review: zo-q2m.2 (R1, reviewer-leaf)

- Bead: zo-q2m.2
- Commit range: c52c57e..838c981
- Reviewed commits: c52c57e, 53fc88d, 838c981
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 838c981

## Findings

No findings.

## Verification notes

- `src/marktide/emitter.py:143-144` now gates text escaping with `MarkdownEmitter._in_noformat()`, and `src/marktide/emitter.py:247-248` / `src/marktide/emitter.py:297-298` maintain `EmitterState.noformat_depth` across the same open-element lifetime that the previous stack scan covered. Text before a noformat element is flushed before the increment, text inside the element is flushed before the decrement, and filtered/unhandled descendants still remain covered by ancestor depth.
- Handler-level `in_noformat(em)` remains the ancestor-only stack-scan helper in `src/marktide/rules/blocks.py:44-46`, so `src/marktide/rules/inline.py:167-195` still renders the current `<code>` / `<kbd>` / `<samp>` element normally while passing through only when an ancestor noformat element exists.
- `src/marktide/emitter.py:255-257` pushes `MarkdownEmitter._buf_target` only after `Frame.buffering` is known, and `src/marktide/emitter.py:269-270` restores it after `MarkdownEmitter._flush_text()` has finalized this element's text but before `handler.end(self)` emits to the parent. That preserves both this element's buffered `Frame.content` and parent-buffer visibility for handlers such as `src/marktide/rules/inline.py:181`.
- `src/marktide/emitter.py:59-60` is equivalent to `src/marktide/emitter.py:44` for strings without boundary newlines, because interior newlines remain part of the regex content group. `src/marktide/emitter.py:140-142` is equivalent to the old two-substitution path for clean text: the skipped cases contain no newline/CR collapse, no tab, and no run of two spaces.

## Commands run

- `uv run python - <<'PY' ...` spot checks for `<code>`, `<kbd>`, `<samp>`, adjacent code spans, and nested noformat cases against `markdownify.markdownify`.
- `uv run --group benchmark pytest tests/unit/marktide/test_block_inline_handlers.py -q` — 74 passed.
- `uv run python - <<'PY' ...` Hypothesis equivalence check for `_split_newlines()` and the whitespace fast-path guard against the original regex behavior — passed 5000 generated examples each.
- `make verify-fidelity` — primary effective 298/298, raw 296/298, streaming parity mismatches 0/1107.
- `make all` — 1492 passed, 1 xfailed.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
