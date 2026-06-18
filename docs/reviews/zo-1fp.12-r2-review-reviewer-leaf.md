# Code Review: zo-1fp.12 (R2, reviewer-leaf)

- Bead: zo-1fp.12
- Commit range: d2f1fc5..c6e1cfa
- Plan doc: docs/design.md, docs/test-plan.md
- Reviewer: reviewer-leaf
- Review commit: c6e1cfa

## Findings

No findings.

## R1 disposition verification

| R1 # | Severity | Status | Verification |
|---|---|---|---|
| 1 | P1 | Resolved | `_Paragraph.end` in `src/html2md/rules/blocks.py` now applies markdownify-style `textwrap.fill` when `Options.wrap=True` / `wrap_width` is set. Targeted comparison against `markdownify.markdownify(..., wrap=True, wrap_width=20)` matched, including a `<br>` hard-break wrapping case. |
| 2 | P1 | Resolved | `_Pre.end` in `src/html2md/rules/blocks.py` now calls `code_language_callback(em.frame)` and uses `result or code_language`. Targeted comparison against markdownify callback output matched, and the empty-result fallback preserved `Options.code_language`. |
| 3 | P2 | Resolved for handler behavior | `_Pre.end` now handles `strip_pre="strip_one"` with one leading/trailing newline removed. Targeted comparisons for `strip`, `strip_one`, and `None` matched markdownify. The remaining `Options.strip_pre` type annotation mismatch is correctly noted in the R1 disposition as options-owner follow-up, not a blocker for this handler bead's runtime behavior. |

## Validation performed

- Read `d2f1fc5` changes to `src/html2md/rules/blocks.py`, `src/html2md/rules/inline.py`, and `tests/unit/html2md/test_block_inline_handlers.py`, plus the R1 disposition appended in `c6e1cfa`.
- Ran `uv run pytest tests/unit/html2md/test_block_inline_handlers.py -q` → `57 passed, 10 xfailed in 0.08s`.
- Ran `uv run ruff check src/html2md/rules/blocks.py src/html2md/rules/inline.py tests/unit/html2md/test_block_inline_handlers.py` → `All checks passed!`.
- Ran targeted `markdownify==1.2.2` comparisons for paragraph wrapping, `<br>` wrapping preservation, `code_language_callback`, callback fallback to `code_language`, and `strip_pre` modes (`strip`, `strip_one`, `None`).

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
