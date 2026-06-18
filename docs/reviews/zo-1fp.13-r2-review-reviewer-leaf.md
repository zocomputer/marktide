# Code Review: zo-1fp.13 (R2, reviewer-leaf)

- Bead: zo-1fp.13
- Commit range: 896a5a1..492103d
- Plan doc: docs/design.md, docs/test-plan.md
- Reviewer: reviewer-leaf
- Review commit: ab40c4d

## Findings

No findings.

## R1 disposition verification

| R1 # | Severity | Status | Verification |
|---|---|---|---|
| 1 | P1 | Resolved | `CaptionHandler` plus `TableHandler.end` passthrough preservation now keeps `<caption>` content before the rendered grid. Upstream `table_with_caption` matches markdownify in both `table_infer_header` modes. |
| 2 | P1 | Resolved | `_normalise_cell_text` now collapses table-cell whitespace with `" ".join(text.split())`. Upstream `table_with_linebreaks` matches markdownify in both `table_infer_header` modes. |
| 3 | P2 | Resolved | `tests/unit/html2md/test_tables.py` now parametrizes the vendored upstream markdownify table corpus for both `table_infer_header` modes and adds explicit caption/multiline-cell regressions. |

## Additional follow-up verification

Commit `492103d` adds standalone table-fragment behavior for `<td>`, `<th>`, `<tr>`, `<tbody>`, and `<thead>` when lxml parses fragments outside a surrounding `<table>`. I compared those fragments against `markdownify==1.2.2` with `strip_document=None`; they matched.

## Validation performed

- Read `896a5a1` and `492103d` changes to `src/html2md/rules/tables.py` and `tests/unit/html2md/test_tables.py`.
- Ran `uv run pytest tests/unit/html2md/test_tables.py -q` → `39 passed in 0.10s`.
- Ran `uv run --group benchmark pytest tests/conformance/test_differential.py -q` → `8 passed in 0.07s`.
- Ran `uv run ruff check src/html2md/rules/tables.py tests/unit/html2md/test_tables.py` → `All checks passed!`.
- Independently re-ran the vendored upstream markdownify table corpus comparison for all 15 table cases × both `table_infer_header` modes; `corpus errs 0`.
- Independently compared standalone fragments (`<td>`, `<th colspan>`, `<tr>`, `<tbody>`, `<thead>`) against `MarkdownConverter(strip_document=None, heading_style="atx")`; all matched.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
