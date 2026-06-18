# Code Review: zo-1fp.11 (R2, reviewer-leaf)

- Bead: zo-1fp.11
- Commit range: eac709e..141c6b6
- Plan doc: docs/design.md, docs/test-plan.md
- Reviewer: reviewer-leaf
- Review commit: 766e1ec

## Findings

No findings against the zo-1fp.11 R1 checklist.

## R1 disposition verification

| R1 # | Severity | Status | Verification |
|---|---|---|---|
| 1 | P1 | Resolved | `eac709e` exposes `MarkdownEmitter.frame` during `handler.end`, resets it in `finally`, and adds nested same-tag regression tests proving distinct attrs/data and closed-frame-vs-parent semantics. Targeted tests/ruff passed during focused re-review. |
| 2 | P1 | Resolved | `e775e46` adds `MarkdownEmitter.drain`, `IncrementalDriver.drain`, per-feed draining in `convert_stream` / `ChunkPump.run`, and non-buffering transparent frames so safe output reaches the drainable root before EOF. Targeted streaming tests and extra chunk-equivalence smoke passed during focused re-review. |
| 3 | P1 | Resolved | `9f12f83` serializes `ChunkPump` parser operations behind a single lock and shields final close to completion. Blocking fake-driver cancellation regression proves `close()` does not overlap an in-flight `feed()` and still runs. Targeted tests/ruff passed during focused re-review. |
| 4 | P2 | Resolved | `141c6b6` ports markdownify's `escape_misc` regex behavior and centralizes text whitespace / noformat escaping / boundary newline collapse. Targeted markdownify comparisons for misc chars, dash/hash/list markers, code no-escape, whitespace normalization, boundary collapse, and UTF-8 fragments matched. |

## Deliberate deferral noted

`blockquote_nested` from `tests/conformance/golden/block_inline_handler_cases.json` still differs by one trailing space (`'> Outer \n> > Inner'` vs `'> Outer\n> > Inner'`). This is item D from misc-leaf's note: text rstrip before a following sibling block requires next-sibling lookahead and was explicitly deferred as a lower-priority emitter/conformance follow-up. It is not part of the original zo-1fp.11 R1 P0/P1/P2 checklist and should be tracked separately if it remains after the next whitespace/lookahead pass.

## Validation performed

- Read `141c6b6` changes to `src/html2md/emitter.py` and `src/html2md/parser.py`.
- Ran targeted suite: `uv run pytest tests/unit/html2md/test_emitter.py tests/unit/html2md/test_streaming.py tests/unit/html2md/test_convert.py tests/unit/html2md/test_parser.py tests/unit/html2md/test_block_inline_handlers.py -q` → `102 passed, 1 xfailed in 0.27s`.
- Ran targeted markdownify comparisons for `escape_misc` chars/dash/hash/list markers, asterisk/underscore escaping, noformat code spans, pre vs paragraph whitespace normalization, child-boundary collapse, and charset-less UTF-8 fragments — all matched.
- Checked the 10 formerly known block/inline xfail cases directly: 9 now match; only the explicitly deferred `blockquote_nested` remains.
- Full `uv run pytest tests/unit/html2md -q` is currently polluted by unrelated in-progress uncommitted block-rule changes in this shared worktree (`test_structural_tags_registered_transparent` now observes a non-transparent `_Div` handler). I did not treat that unrelated concurrent change as part of this foundation re-review.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
