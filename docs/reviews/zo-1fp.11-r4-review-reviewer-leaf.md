# Code Review: zo-1fp.11 (R4, reviewer-leaf)

- Bead: zo-1fp.11
- Related bead: zo-1fp.19
- Commit range: 5a7951a, af097fc, 4febd02 (targeted R3/R4 follow-ups)
- Plan doc: docs/design.md
- Reviewer: reviewer-leaf
- Review commit: 4febd02

## Findings

No findings.

## Verification

The R3 follow-ups are resolved or dispositioned:

1. **`blockquote_nested` regression is enforced.** `tests/unit/html2md/test_block_inline_handlers.py` no longer xfails `blockquote_nested`, and `convert(b"<blockquote>Outer <blockquote>Inner</blockquote></blockquote>")` returns `"> Outer\n> > Inner"`.
2. **Streaming chunk-invariance fix is sound.** `src/html2md/emitter.py:86-93` adds the O(1) resumable root-fold state (`_carry`, `_tail`) plus consecutive `data()` coalescing (`_text_buf`). `src/html2md/emitter.py:217-293` flushes coalesced text at the right non-data boundaries (`start`, `end`, `comment`, `close`), and `src/html2md/emitter.py:297-358` folds root children resumably while holding back trailing newlines until they are stable.
3. **CDATA with angle brackets is accepted as a parser divergence, not an emitter bug.** lxml/libxml2 does not expose the leading `>` from `foo <![CDATA[>&<]]>` in target-parser events, so the original `>&<` text is unrecoverable without a separate pre-lxml source rewrite layer. Plain CDATA (`<![CDATA[foobar]]>`) is preserved. The divergence is logged in `tests/conformance/allowed_divergences.toml` and `docs/conformance-failure-analysis.md` by `4febd02`.
4. **The chunk-invariance harness now covers the missed structural boundary.** `tests/component/test_chunk_invariance.py:62-126` adds structural-boundary offset discovery, and `tests/component/test_chunk_invariance.py:203-218` exercises the implicit `<title>`/head/body boundary repro and nearby controls across every split point.

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
