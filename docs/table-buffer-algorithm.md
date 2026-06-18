# Table rule / bounded table-buffer algorithm draft

Date: 2026-06-17  
Owner: coder-3-leaf  
Target bead: `zo-1fp.13` (`src/html2md/rules/tables.py` + `src/html2md/state.py` table state)

## Source behavior to match

`markdownify==1.2.2` implements table output in `markdownify.MarkdownConverter.convert_table`, `convert_tr`, `convert_td`, and `convert_th`:

- `convert_table(el, text, ...)` returns `"\n\n" + text.strip() + "\n\n"`.
- `convert_td` / `convert_th` strip cell text, replace internal newlines with spaces, and emit one pipe per colspan slot:
  - `colspan = max(1, min(1000, int(colspan)))` if the attr is all digits, else `1`.
  - cell text shape is `" " + normalized_text + " |" * colspan`.
- `convert_tr` decides header/separator behavior row-by-row:
  - `cells = el.find_all(['td', 'th'])`.
  - `is_first_row = el.find_previous_sibling() is None` within the row's direct parent.
  - `is_headrow = all(cells are th) or (parent is thead and parent has exactly one tr)`.
  - `is_head_row_missing = (first row and parent is not tbody) or (first row in tbody and table has no thead)`.
  - If `(is_headrow or (is_head_row_missing and table_infer_header)) and is_first_row`, append separator under this row.
  - Else if `(is_head_row_missing and not table_infer_header) or first row at table start`, prepend an empty synthetic header + separator before this row.
- Default `table_infer_header` is `False`.

The hand-authored golden cases in `tests/conformance/golden/edge_cases.json` lock the important outputs:

- `table_th_header_inference` → explicit `<th>` first row becomes the real header.
- `table_td_first_row_not_header` → first `<td>` row gets synthetic empty header when `table_infer_header=False`.
- `table_colspan_and_ragged_rows` → colspan expands width; ragged rows are not padded beyond their actual cells.

## State objects

Add a table stack to `EmitterState` so nested/malformed tables do not corrupt outer state:

```python
@dataclass(slots=True)
class TableCell:
    tag: Literal["td", "th"]
    text_parts: list[str]
    colspan: int = 1

@dataclass(slots=True)
class TableRow:
    parent_tag: str          # table | thead | tbody | tfoot | unknown
    cells: list[TableCell]
    row_index_in_parent: int # markdownify find_previous_sibling() equivalent

@dataclass(slots=True)
class TableBuffer:
    rows: list[TableRow]
    parent_row_counts: dict[int, int]
    has_thead: bool
    section_stack: list[tuple[int, str]] # parser depth + tag for thead/tbody/tfoot
```

Boundedness: buffer is per currently-open table and flushed on `</table>`. This is bounded by a single table's row/cell content, not by document size. It is the intended localized reservoir from design §4.3 / Alien Artifacts §11.2. Non-table output continues to flush normally; table output is the only block held until its safe-flush barrier (`</table>`).

## Event handling pseudocode

```python
def start_table(state):
    state.table_stack.append(TableBuffer(rows=[], parent_row_counts={}, has_thead=False, section_stack=[]))


def start_table_section(state, tag, depth):
    table = state.table_stack[-1]
    if tag == "thead":
        table.has_thead = True
    table.section_stack.append((depth, tag))


def end_table_section(state, tag, depth):
    table = state.table_stack[-1]
    pop matching (depth, tag) from table.section_stack


def current_table_parent_tag(state) -> str:
    table = state.table_stack[-1]
    return table.section_stack[-1][1] if table.section_stack else "table"


def start_tr(state, depth):
    table = state.table_stack[-1]
    parent = current_table_parent_tag(state)
    parent_key = id/current section frame, or 0 for direct table
    row_index = table.parent_row_counts.get(parent_key, 0)
    table.parent_row_counts[parent_key] = row_index + 1
    state.current_table_row = TableRow(parent_tag=parent, cells=[], row_index_in_parent=row_index)


def start_cell(state, tag, attrs):
    colspan = parse_colspan(attrs.get("colspan"))
    state.current_table_cell = TableCell(tag=tag, text_parts=[], colspan=colspan)


def data_in_table_cell(state, text):
    # Reuse normal inline rendering for emphasis/link/code inside cells, but route the
    # resulting Markdown fragments into current_table_cell.text_parts instead of the global sink.
    state.current_table_cell.text_parts.append(rendered_fragment)


def end_cell(state):
    row = state.current_table_row
    row.cells.append(state.current_table_cell)
    state.current_table_cell = None


def end_tr(state):
    table = state.table_stack[-1]
    table.rows.append(state.current_table_row)
    state.current_table_row = None


def end_table(state):
    table = state.table_stack.pop()
    emit("\n\n" + render_table(table).strip() + "\n\n")
```

## Rendering algorithm

Render once at `</table>` in original row order:

```python
def render_table(table, *, table_infer_header=False):
    out = []
    for row in table.rows:
        cells = row.cells
        is_first_row = row.row_index_in_parent == 0
        is_headrow = (
            cells and all(cell.tag == "th" for cell in cells)
        ) or (
            row.parent_tag == "thead" and count_rows_with_parent(row.parent_id) == 1
        )
        is_head_row_missing = (
            (is_first_row and row.parent_tag != "tbody")
            or (is_first_row and row.parent_tag == "tbody" and not table.has_thead)
        )
        full_colspan = sum(cell.colspan for cell in cells)

        if ((is_headrow or (is_head_row_missing and table_infer_header)) and is_first_row):
            out.append(render_row(cells))
            out.append(separator(full_colspan))
        elif ((is_head_row_missing and not table_infer_header) or is_first_table_start_row(row, table)):
            out.append(empty_header(full_colspan))
            out.append(separator(full_colspan))
            out.append(render_row(cells))
        else:
            out.append(render_row(cells))
    return "\n".join(out)
```

`render_row(cells)` must mirror markdownify's cell concatenation exactly:

```python
def render_cell(cell):
    text = "".join(cell.text_parts).strip().replace("\n", " ")
    return " " + text + " |" * cell.colspan


def render_row(cells):
    # markdownify convert_tr prepends the leading pipe around the concatenated cell text.
    return "|" + "".join(render_cell(cell) for cell in cells)
```

`separator(n)` is `"| " + " | ".join(["---"] * n) + " |"`.  
`empty_header(n)` is `"| " + " | ".join([""] * n) + " |"`.

## Specific edge rules

1. **Header inference**
   - Default `table_infer_header=False` emits synthetic empty header for a first `<td>` row.
   - Explicit all-`<th>` first row emits that row as header + separator.
   - A single-row `<thead>` is treated as header even if cells are `<td>`.
   - Multi-row `<thead>` does **not** make every row a header; only all-`th` rows qualify, matching `len(thead.find_all('tr')) == 1` guard.

2. **Colspan**
   - Parse only digit-only values.
   - Clamp to `[1, 1000]`.
   - Expand separator/empty-header width by colspan.
   - Cell text occupies the first logical column and the extra colspan slots are emitted as empty `|` slots (`| Name | Score | |`).

3. **Ragged rows**
   - Do not globally pad data rows to the header width. Markdownify outputs only actual cell pipes for ragged rows (`| Bob | 9 |`), even under a 3-column header.
   - Separator width is based on the row that triggered the separator, not later max width.

4. **Flush behavior**
   - Do not emit partial table rows before `</table>` because the first row/header decision can require prepending a synthetic header above already-seen row content.
   - Flush exactly once on `</table>` with surrounding blank lines equivalent to `convert_table`: two leading newlines, stripped table body, two trailing newlines.
   - If parser recovery closes a table implicitly, the target parser should still issue `end("table")`; if not, `close()` must flush any open `TableBuffer` defensively.

5. **Nested tables**
   - Use `table_stack`. Inner table output should be captured into the current outer cell's text buffer if it appears inside a cell, then normalized by the cell's newline-to-space rule. This mirrors BeautifulSoup's recursive text conversion better than writing inner table output to the global sink.

6. **Non-cell text inside table**
   - Text outside `<td>/<th>` is ignored for Markdown table structure unless the foundation's generic inline pipeline intentionally preserves it. Markdownify row conversion only uses `td`/`th` descendants for row cells.

## Implementation checklist for `zo-1fp.13`

- Add `TableBuffer`, `TableRow`, `TableCell` to `src/html2md/state.py` once misc-leaf's foundation types land.
- Add `src/html2md/rules/tables.py` handlers for `table`, `thead`, `tbody`, `tfoot`, `tr`, `td`, `th`.
- Route inline fragments into `TableCell.text_parts` while `state.current_table_cell is not None`.
- Add tests for the three table cases in `tests/conformance/golden/edge_cases.json` first; then add focused unit tests for invalid/huge `colspan`, `<thead><tr><td>`, multi-row `<thead>`, and ragged rows.
