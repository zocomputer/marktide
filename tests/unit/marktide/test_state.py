"""EmitterState — pushdown stack + context tracking."""

from __future__ import annotations

from marktide.state import (
    EmitterState,
    Frame,
    ListContext,
    TableBuffer,
    TableCell,
    TableRow,
)


def test_push_pop_depth_top() -> None:
    s = EmitterState()
    assert s.depth == 0 and s.top is None
    f1 = s.push("div", {"class": "x"})
    assert isinstance(f1, Frame) and s.top is f1 and s.depth == 1
    s.push("p", {})
    assert s.top.tag == "p" and s.depth == 2
    popped = s.pop()
    assert popped.tag == "p" and s.depth == 1 and s.top.tag == "div"
    s.pop()
    assert s.pop() is None  # pop on empty is safe


def test_frame_carries_attrs_content_and_data() -> None:
    s = EmitterState()
    f = s.push("a", {"href": "/x"})
    assert f.attrs == {"href": "/x"}
    f.content.append("text")
    f.data["href"] = "/x"
    assert f.content == ["text"] and f.data["href"] == "/x"


def test_has_ancestor() -> None:
    s = EmitterState()
    s.push("table", {})
    s.push("tr", {})
    s.push("td", {})
    assert s.has_ancestor("table") is True
    assert s.has_ancestor("ul", "ol") is False
    assert s.has_ancestor("tr", "ul") is True


def test_context_predicates() -> None:
    s = EmitterState()
    assert not s.in_pre and not s.in_table
    s.pre_depth += 1
    assert s.in_pre
    s.table_stack.append(TableBuffer())
    assert s.in_table


def test_list_and_table_contexts_construct() -> None:
    lc = ListContext(ordered=True, index=1, marker="*")
    assert lc.ordered and lc.index == 1 and lc.marker == "*"
    tb = TableBuffer()
    assert tb.rows == [] and tb.in_header is False and tb.current_row is None
    assert tb.current_cell is None and tb.parent_row_counts == {}

    row = TableRow(
        parent_tag="table", parent_key=0, parent_order=0, row_index_in_parent=0
    )
    row.cells.append(TableCell(tag="th", text="Name"))
    tb.current_row = row
    assert tb.current_row.cells[0].text == "Name"
