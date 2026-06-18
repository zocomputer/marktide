# Code Review: zo-1fp.19 (R1, reviewer-leaf)

- Bead: zo-1fp.19
- Commit range: af097fc, 4febd02
- Plan doc: docs/design.md §9.1 chunk-boundary invariance
- Reviewer: reviewer-leaf
- Review commit: 4febd02

## Findings

No findings.

## Verification

`zo-1fp.19` fixes the central `convert_stream` invariant:

1. `src/html2md/emitter.py:297-358` replaces the previous non-resumable root newline collapse with `_fold_children`, carrying only the last child's unstable trailing newlines in `MarkdownEmitter._carry` and withholding document-trailing newlines in `MarkdownEmitter._tail`.
2. `src/html2md/emitter.py:275-286` coalesces consecutive lxml `data()` callbacks before whitespace normalization, which removes feed-boundary dependence when lxml splits a single text node across chunks.
3. `src/html2md/emitter.py:217`, `src/html2md/emitter.py:242`, `src/html2md/emitter.py:288`, and `src/html2md/emitter.py:321` flush that text coalescing at `start`, `end`, `comment`, and `close`, so text nodes are finalized before the next structural decision.
4. `tests/unit/html2md/test_streaming.py:71-89` adds targeted unit coverage for title/head/textarea/list/blockquote structural boundaries and chunk sizes 1, 2, 3, 7, and 64.
5. `tests/component/test_chunk_invariance.py:62-126` and `tests/component/test_chunk_invariance.py:203-218` strengthen the component harness so the exact missed implicit `<title>` + newline + body-block repro and controls are split at every possible boundary.

## Tests / checks run

- `uv run pytest tests/unit/html2md/test_streaming.py tests/unit/html2md/test_rules.py tests/component/test_chunk_invariance.py -q` → 1180 passed
- `uv run pytest tests/e2e -q` → 16 passed, 4 skipped, 1 xpassed
- `uv run ruff check src/html2md/emitter.py tests/unit/html2md/test_streaming.py tests/unit/html2md/test_rules.py` → passed
- `uv run pytest tests/unit/html2md tests/conformance -q` → 330 passed
- Independent all-corpus stream-vs-one-shot check over 1107 conformance cases × chunk sizes `(1, 2, 3, 7, 64)` → 0 failures
- Independent randomized resumable-fold equivalence check across 33,680 child/drain/`strip_document` combinations → 0 failures

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
