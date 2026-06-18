"""DSST register-memory invariant (design §11): the live register footprint of the
streaming converter is O(open-depth + largest-open-block + table-width), NOT O(input).

The converter is a deterministic streaming tree transducer whose string-valued
registers are the per-frame output buffers (a pushdown stack) plus a finite set of
bounded scalar registers (the sibling-whitespace deferral, the collapse carry/tail, the
text-coalescing buffer) and the bounded table reservoir. Copyless register updates —
each frame's buffer is appended into its nearest buffering ancestor exactly once at
``end`` and drained output is released — keep resident register memory bounded by the
currently-open path, not by how much input has been consumed.
"""

from __future__ import annotations

from html2md.emitter import MarkdownEmitter
from html2md.options import Options
from html2md.parser import IncrementalDriver


def register_footprint(em: MarkdownEmitter) -> int:
    """Bytes held in the live transducer registers (excludes already-drained output)."""
    total = len(em._carry) + len(em._tail) + sum(len(s) for s in em._text_buf)
    for frame in em.state.stack:
        total += sum(len(s) for s in frame.content) + len(frame.pending_ws)
    for table in em.state.table_stack:           # bounded table reservoir
        for row in table.rows:
            total += sum(len(cell.text) for cell in row.cells)
        if table.current_row is not None:
            total += sum(len(cell.text) for cell in table.current_row.cells)
    return total


def _peak_footprint(html: bytes, *, chunk: int = 4096) -> int:
    """Stream `html` through the driver, draining each chunk, and return the peak live
    register footprint observed between feeds."""
    driver = IncrementalDriver()
    peak = 0
    for i in range(0, len(html), chunk):
        driver.feed(html[i:i + chunk])
        driver.drain()  # release committed output, as real streaming does
        peak = max(peak, register_footprint(driver.emitter))
    driver.close()
    return peak


def test_register_footprint_does_not_scale_with_input() -> None:
    # Many shallow blocks: 4× the blocks (4× the input) must NOT 4× the peak register
    # footprint — it is bounded by open depth + one block, independent of document size.
    def doc(n: int) -> bytes:
        return b"".join(
            f"<p>block number {i} with a little text content</p>".encode()
            for i in range(n)
        )

    peak_small = _peak_footprint(doc(2_000))
    peak_large = _peak_footprint(doc(8_000))  # 4× input
    assert peak_large < peak_small * 2, (
        f"register footprint scaled with input: {peak_small} -> {peak_large}"
    )
    # absolute bound: a handful of open frames each holding ~one small block
    assert peak_small < 20_000, peak_small


def test_nesting_depth_bounds_footprint_not_length() -> None:
    # A long flat document and a short deep one: footprint tracks DEPTH, not length.
    flat = b"<p>x</p>" * 5_000
    deep = b"<div>" * 40 + b"<p>x</p>" + b"</div>" * 40
    assert _peak_footprint(flat) < 20_000
    assert _peak_footprint(deep) < 20_000


def test_single_giant_block_is_the_documented_exception() -> None:
    # The one way to inflate the bound is a single huge open block (design §4.7 worst
    # case): O(largest open block), still not O(whole document) when blocks are bounded.
    giant = b"<p>" + (b"word " * 200_000) + b"</p>"
    peak = _peak_footprint(giant)
    assert peak > 100_000  # the open <p> register holds its (large) content...
    # ...but a document of many SMALL blocks of the same total size stays bounded:
    many_small = b"<p>word</p>" * 100_000
    assert _peak_footprint(many_small) < 20_000


def test_table_reservoir_bounded_by_table_not_document() -> None:
    # The table buffer is the localized bounded register-array (design §11): a table is
    # buffered until </table>, bounded by the table's own size, independent of how much
    # document precedes/follows it.
    prefix = b"<p>x</p>" * 10_000
    table = b"<table>" + b"<tr><td>a</td><td>b</td></tr>" * 50 + b"</table>"
    peak_with_prefix = _peak_footprint(prefix + table)
    peak_table_only = _peak_footprint(table)
    # the preceding 10k paragraphs do not inflate the table-time footprint
    assert peak_with_prefix < peak_table_only + 20_000


def test_text_coalescing_buffer_is_released() -> None:
    # The coalescing buffer holds at most one text node and is flushed on the next
    # non-data event, so it does not accumulate across a long run of text+element pairs.
    html = b"".join(b"text<span>x</span>" for _ in range(5_000))
    assert _peak_footprint(html) < 20_000


def test_options_does_not_change_invariant() -> None:
    driver = IncrementalDriver(Options(chunk_size=64 * 1024))
    html = b"<p>block</p>" * 5_000
    peak = 0
    for i in range(0, len(html), 4096):
        driver.feed(html[i:i + 4096])
        driver.drain()
        peak = max(peak, register_footprint(driver.emitter))
    driver.close()
    assert peak < 20_000
