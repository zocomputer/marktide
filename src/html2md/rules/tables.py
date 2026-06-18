"""Table rules: table/thead/tbody/tfoot/tr/td/th.

Tables are the one construct that buffers: Markdown needs the header row and every
cell width before any row can be emitted (column count + alignment), so a ``<table>``
accumulates into a bounded :class:`~html2md.state.TableBuffer` and flushes the grid at
``</table>`` (design §4.3, §4.7). The buffer is bounded by table dimensions, never by
document size.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ..state import TableBuffer, TableCell, TableRow, TableSection
from .base import TagHandler

_TABLE_PARENT_KEY = 0
_MAX_COLSPAN = 1000


def _parse_colspan(attrs: Mapping[str, str]) -> int:
    value = attrs.get("colspan", "")
    if not value.isdigit():
        return 1
    return max(1, min(_MAX_COLSPAN, int(value)))


def _normalise_cell_text(text: str) -> str:
    # markdownify sees table-cell text after normal whitespace collapse, then strips.
    return " ".join(text.split())


def _row_slot_count(cells: Iterable[TableCell]) -> int:
    return sum(cell.colspan for cell in cells)


def _render_cell(cell: TableCell) -> str:
    return " " + _normalise_cell_text(cell.text) + " |" * cell.colspan


def _render_cells(cells: Iterable[TableCell]) -> str:
    return "|" + "".join(_render_cell(cell) for cell in cells)


def _empty_header(columns: int) -> str:
    return "| " + " | ".join([""] * columns) + " |"


def _separator(columns: int) -> str:
    return "| " + " | ".join(["---"] * columns) + " |"


def _is_head_row(table: TableBuffer, row: TableRow) -> bool:
    parent_row_count = table.parent_row_counts.get(row.parent_key, 0)
    return (bool(row.cells) and all(cell.tag == "th" for cell in row.cells)) or (
        row.parent_tag == "thead" and parent_row_count == 1
    )


def _is_head_row_missing(table: TableBuffer, row: TableRow) -> bool:
    if row.row_index_in_parent != 0:
        return False
    if row.parent_tag != "tbody":
        return True
    return not table.has_thead


def _should_prepend_empty_header(
    table: TableBuffer, row: TableRow, *, infer_header: bool
) -> bool:
    if row.row_index_in_parent != 0:
        return False
    if _is_head_row_missing(table, row) and not infer_header:
        return True
    return row.parent_tag == "table" or (
        row.parent_tag == "tbody" and row.parent_order == 1
    )


def render_table(table: TableBuffer, *, infer_header: bool = False) -> str:
    """Render a captured table buffer using markdownify-compatible header rules."""
    lines: list[str] = []
    for row in table.rows:
        columns = _row_slot_count(row.cells)
        if columns == 0:
            continue
        is_head_row = _is_head_row(table, row)
        is_head_row_missing = _is_head_row_missing(table, row)
        if (
            is_head_row or (is_head_row_missing and infer_header)
        ) and row.row_index_in_parent == 0:
            lines.append(_render_cells(row.cells))
            lines.append(_separator(columns))
        elif _should_prepend_empty_header(table, row, infer_header=infer_header):
            lines.append(_empty_header(columns))
            lines.append(_separator(columns))
            lines.append(_render_cells(row.cells))
        else:
            lines.append(_render_cells(row.cells))
    return "\n".join(lines)


class TableHandler:
    __slots__ = ()

    def start(self, em, attrs: Mapping[str, str]) -> None:
        em.state.table_stack.append(TableBuffer())

    def end(self, em) -> None:
        if not em.state.table_stack:
            return
        table = em.state.table_stack.pop()
        markdown = render_table(table, infer_header=em.options.table_infer_header)
        passthrough = em.content.strip()
        pieces = [piece for piece in (passthrough, markdown.strip()) if piece]
        if pieces:
            em.emit("\n\n" + "\n\n".join(pieces) + "\n\n")


class CaptionHandler:
    __slots__ = ()

    def start(self, em, attrs: Mapping[str, str]) -> None:
        return None

    def end(self, em) -> None:
        text = em.content.strip()
        if text:
            em.emit(text + "\n\n")


class TableSectionHandler:
    __slots__ = ("tag",)

    def __init__(self, tag: str) -> None:
        self.tag = tag

    def start(self, em, attrs: Mapping[str, str]) -> None:
        if not em.state.table_stack:
            return
        table = em.state.table_stack[-1]
        section = TableSection(
            tag=self.tag,
            key=table.next_parent_key,
            order=table.next_section_order,
        )
        table.next_parent_key += 1
        table.next_section_order += 1
        table.section_stack.append(section)
        table.in_header = self.tag == "thead"
        if self.tag == "thead":
            table.has_thead = True

    def end(self, em) -> None:
        if not em.state.table_stack:
            em.emit(em.content)
            return
        table = em.state.table_stack[-1]
        for index in range(len(table.section_stack) - 1, -1, -1):
            if table.section_stack[index].tag == self.tag:
                del table.section_stack[index]
                break
        table.in_header = bool(
            table.section_stack and table.section_stack[-1].tag == "thead"
        )


class TableRowHandler:
    __slots__ = ()

    def start(self, em, attrs: Mapping[str, str]) -> None:
        if not em.state.table_stack:
            frame = em.state.top
            if frame is not None:
                parent = em.state.stack[-2] if len(em.state.stack) >= 2 else None
                parent_tag = (
                    parent.tag
                    if parent is not None and parent.tag in {"thead", "tbody", "tfoot"}
                    else "table"
                )
                frame.data["table_parent_tag"] = parent_tag
                frame.data["table_cells"] = []
            return
        table = em.state.table_stack[-1]
        if table.section_stack:
            section = table.section_stack[-1]
            parent_tag = section.tag
            parent_key = section.key
            parent_order = section.order
        else:
            parent_tag = "table"
            parent_key = _TABLE_PARENT_KEY
            parent_order = 0
        row_index = table.parent_row_counts.get(parent_key, 0)
        table.current_row = TableRow(
            parent_tag=parent_tag,
            parent_key=parent_key,
            parent_order=parent_order,
            row_index_in_parent=row_index,
        )

    def end(self, em) -> None:
        if not em.state.table_stack:
            if em.frame is None:
                return
            cells = em.frame.data.get("table_cells")
            if not isinstance(cells, list):
                em.emit(em.content)
                return
            parent_tag = str(em.frame.data.get("table_parent_tag", "table"))
            row = TableRow(
                parent_tag=parent_tag,
                parent_key=_TABLE_PARENT_KEY,
                parent_order=0,
                row_index_in_parent=0,
                cells=cells,
            )
            table = TableBuffer(
                rows=[row],
                parent_row_counts={_TABLE_PARENT_KEY: 1},
                has_thead=parent_tag == "thead",
            )
            em.emit(
                render_table(table, infer_header=em.options.table_infer_header) + "\n"
            )
            return
        table = em.state.table_stack[-1]
        row = table.current_row
        if row is None:
            return
        table.rows.append(row)
        table.parent_row_counts[row.parent_key] = row.row_index_in_parent + 1
        table.current_row = None


class TableCellHandler:
    __slots__ = ("tag",)

    def __init__(self, tag: str) -> None:
        self.tag = tag

    def start(self, em, attrs: Mapping[str, str]) -> None:
        return None

    def end(self, em) -> None:
        if em.frame is None:
            return
        cell = TableCell(
            tag=self.tag,
            text=em.content,
            colspan=_parse_colspan(em.frame.attrs),
        )
        if not em.state.table_stack:
            parent = em.state.top
            cells = (
                parent.data.get("table_cells")
                if parent is not None and parent.tag == "tr"
                else None
            )
            if isinstance(cells, list):
                cells.append(cell)
            else:
                em.emit(_render_cell(cell))
            return
        table = em.state.table_stack[-1]
        if table.current_row is None:
            return
        table.current_row.cells.append(cell)
        if self.tag == "th":
            table.has_header = True


HANDLERS: dict[str, TagHandler] = {
    "table": TableHandler(),
    "thead": TableSectionHandler("thead"),
    "tbody": TableSectionHandler("tbody"),
    "tfoot": TableSectionHandler("tfoot"),
    "caption": CaptionHandler(),
    "tr": TableRowHandler(),
    "td": TableCellHandler("td"),
    "th": TableCellHandler("th"),
}
