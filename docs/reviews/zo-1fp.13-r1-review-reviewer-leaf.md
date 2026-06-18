# Code Review: zo-1fp.13 (R1, reviewer-leaf)

- Bead: zo-1fp.13
- Commit range: eac709e..ec758bb
- Plan doc: docs/design.md, docs/test-plan.md
- Reviewer: reviewer-leaf
- Review commit: 91fd376

## Findings

### P1 - `<caption>` content inside tables is dropped

**Location:** `src/html2md/rules/tables.py:102-114`, `src/html2md/rules/tables.py:213-221`

**Problem**
Markdownify has an explicit `convert_caption` behavior: caption text is emitted before the table, separated by blank lines. The table implementation registers handlers for `table`, `thead`, `tbody`, `tfoot`, `tr`, `td`, and `th`, but not `caption`. Because `MarkdownEmitter` buffers child output into the current `<table>` frame, unhandled `<caption>` content becomes part of `em.content` for the table frame. `TableHandler.end` then ignores `em.content` entirely and emits only `render_table(table, ...)`, so the caption is lost.

Repro:

```python
html = "TEXT<table><caption>Caption</caption><tbody><tr><td>Firstname</td><td>Lastname</td><td>Age</td></tr></tbody></table>"
```

`markdownify.markdownify(html, table_infer_header=False).strip()` returns:

```text
TEXT

Caption

|  |  |  |
| --- | --- | --- |
| Firstname | Lastname | Age |
```

`html2md.convert(html, options=Options(table_infer_header=False)).strip()` currently returns:

```text
TEXT

|  |  |  |
| --- | --- | --- |
| Firstname | Lastname | Age |
```

The same data loss occurs with `table_infer_header=True`.

**Suggested fix**
Implement a `caption` handler matching markdownify (`text.strip() + "\n\n"`) and ensure `TableHandler.end` preserves non-row rendered table-frame content (captions and any other passthrough children) before the rendered grid. Add explicit unit/golden coverage for `tests/conformance/fixtures/markdownify/tests/test_tables.py::table_with_caption` with both `table_infer_header=False` and `table_infer_header=True`.

---

### P1 - Table cell newline/indentation normalization leaves repeated spaces

**Location:** `src/html2md/rules/tables.py:28-30`, `tests/unit/html2md/test_tables.py:68-78`

**Problem**
`_normalise_cell_text` only does `text.strip().replace("\n", " ")`. Markdownify's table cells run through its normal text whitespace collapse before `convert_td` / `convert_th`, so multi-line indented cells collapse internal newline+indentation to a single space. The current implementation preserves indentation spaces after replacing newlines, so upstream markdownify table fixtures diverge.

Repro using the upstream markdownify `table_with_linebreaks` fixture:

```html
<td>Smith
        Jackson</td>
```

Markdownify output:

```text
| Jill | Smith Jackson | 50 |
| Eve | Jackson Smith | 94 |
```

Current html2md output:

```text
| Jill | Smith         Jackson | 50 |
| Eve | Jackson         Smith | 94 |
```

This affects both `table_infer_header=False` and `table_infer_header=True`.

**Suggested fix**
Normalize table cell text the same way markdownify observes it: collapse newline/space/tab runs inside cell content to a single space before trimming/rendering. Add a regression copied from `tests/conformance/fixtures/markdownify/tests/test_tables.py::table_with_linebreaks` for both `table_infer_header` modes.

---

### P2 - Table tests do not cover the upstream markdownify table corpus

**Location:** `tests/unit/html2md/test_tables.py:8-78`, `tests/conformance/fixtures/markdownify/tests/test_tables.py:1-337`

**Problem**
The committed table tests cover the core edge cases in `tests/conformance/golden/edge_cases.json`, but they do not run or reproduce the full upstream markdownify table corpus that is already vendored under `tests/conformance/fixtures/markdownify/tests/test_tables.py`. That corpus contains the two P1 failures above (`table_with_caption`, `table_with_linebreaks`) plus other table shape combinations (`thead`/`tbody`, missing text, multiple head rows, undefined colspan). Because the differential harness currently passes without exercising these table fixtures, regressions can slip through even though the source corpus exists locally.

**Suggested fix**
Add a focused table-conformance test that iterates the upstream markdownify table fixtures (or copies them into generated golden JSON) for both `table_infer_header` modes and compares `html2md.convert(...).strip()` to the markdownify oracle. If the full upstream corpus is too broad for this bead because some inline/link handlers are still landing, at minimum add the pure-table cases and mark cases requiring not-yet-landed inline/link handlers with explicit TODOs tied to the dependent bead.

## Validation performed

- Read `src/html2md/state.py`, `src/html2md/rules/tables.py`, `tests/unit/html2md/test_state.py`, and `tests/unit/html2md/test_tables.py`.
- Ran `uv run pytest tests/unit/html2md/test_tables.py -q` → `5 passed in 0.05s`.
- Ran `uv run --group benchmark pytest tests/conformance/test_differential.py -q` → `4 passed in 0.06s`.
- Independently compared the upstream markdownify table fixtures in `tests/conformance/fixtures/markdownify/tests/test_tables.py` against `html2md.convert`; found divergences for `table_with_caption` and `table_with_linebreaks` in both `table_infer_header` modes.

## Summary

3 findings: 0 P0, 2 P1, 1 P2, 0 P3

**Verdict**: Not approved

The bounded row/cell buffer and the main header/colspan paths look coherent, but table fidelity is not yet complete against markdownify's own table corpus: captions are dropped and multi-line cell whitespace is not normalized like markdownify. Fix those before closing zo-1fp.13.

## Disposition

| # | Severity | Finding | Disposition | Commit | Notes |
|---|----------|---------|-------------|--------|-------|
| 1 | P1 | `<caption>` content inside tables is dropped | Incorporated | this commit | Added `CaptionHandler` and changed `TableHandler.end` to preserve non-row rendered table-frame content before the rendered grid. |
| 2 | P1 | Table cell newline/indentation normalization leaves repeated spaces | Incorporated | this commit | Changed table cell normalization to collapse whitespace runs before rendering, matching markdownify's observed table-cell text. |
| 3 | P2 | Table tests do not cover the upstream markdownify table corpus | Incorporated | this commit | Added parametrized coverage over all vendored upstream markdownify table HTML cases for both `table_infer_header` modes, plus explicit caption and multiline-cell regressions. |
