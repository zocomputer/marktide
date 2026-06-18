"""DSST register-memory invariant (design §11): the live register footprint of the
streaming converter is O(open-depth + largest-open-block + table-width), NOT O(input).

The converter is a deterministic streaming tree transducer whose string-valued
registers are the per-frame output buffers (a pushdown stack), the streamed-root
register, a finite set of bounded scalar registers (the sibling-whitespace deferral,
the collapse carry/tail, the text-coalescing buffer), and the bounded table reservoir.
Copyless register updates — each frame's buffer is appended into its nearest buffering
ancestor exactly once at ``end``, and the streamed root is released by ``drain()`` —
keep resident register memory bounded by the currently-open path plus what one feed
produced before the next drain, never by how much input has been consumed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from html2md.emitter import MarkdownEmitter
from html2md.options import Options
from html2md.parser import IncrementalDriver

# The 100 MiB xlarge fixture is gitignored (regenerated, not committed), so the
# fixture-backed check below is skip-if-absent; the fast representative validation
# (test_large_input_streams_in_bounded_memory) is the always-run one.
_XLARGE = Path(__file__).resolve().parents[3] / "benchmarks" / "fixtures" / "xlarge.html"


def register_footprint(em: MarkdownEmitter) -> int:
    """Bytes held in the live transducer registers, INCLUDING the streamed-root register
    (committed-but-not-yet-drained output) so root accumulation regressions are caught."""
    total = len(em._carry) + len(em._tail) + sum(len(s) for s in em._text_buf)
    total += sum(len(s) for s in em.root)         # streamed-root register (pre-drain)
    for frame in em.state.stack:
        total += sum(len(s) for s in frame.content) + len(frame.pending_ws)
    for table in em.state.table_stack:            # bounded table reservoir
        for row in table.rows:
            total += sum(len(cell.text) for cell in row.cells)
        if table.current_row is not None:
            total += sum(len(cell.text) for cell in table.current_row.cells)
    return total


def _root_bytes(em: MarkdownEmitter) -> int:
    return sum(len(s) for s in em.root)


def _peak_footprint(html: bytes, *, chunk: int = 4096) -> int:
    """Stream `html` through the driver and return the peak live register footprint,
    sampled AFTER each feed but BEFORE the drain — so the streamed-root register's
    accumulation between drains is observed, not hidden by the drain that follows."""
    driver = IncrementalDriver()
    peak = 0
    for i in range(0, len(html), chunk):
        driver.feed(html[i:i + chunk])
        peak = max(peak, register_footprint(driver.emitter))  # before drain
        driver.drain()                                        # release committed output
    driver.close()
    return peak


def test_register_footprint_does_not_scale_with_input() -> None:
    # Many shallow blocks: 4× the blocks (4× the input) must NOT 4× the peak register
    # footprint — it is bounded by open depth + one block + one feed's output, never the
    # document size.
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
    assert peak_small < 64_000, peak_small  # bounded by depth + block + one 4 KiB feed


def test_drain_releases_the_root_register() -> None:
    # Feed enough that the parser flushes completed blocks into root, then assert drain()
    # releases that register (the streaming memory-release mechanism). Without this,
    # root would grow O(document) and the footprint bound would be false.
    html = b"".join(f"<p>block{i:05d}</p>".encode() for i in range(3_000))
    driver = IncrementalDriver()
    driver.feed(html)                       # one big feed → parser flushes most blocks
    before = _root_bytes(driver.emitter)
    assert before > 0, "parser did not flush any completed blocks to root"
    drained = driver.drain()
    after = _root_bytes(driver.emitter)
    assert drained, "drain returned nothing despite a populated root"
    assert after < before, f"drain did not release root: {before} -> {after}"
    # root holds at most the unstable trailing region after a drain
    assert after < 16, after
    driver.close()


def test_large_input_streams_in_bounded_memory() -> None:
    # xlarge-style validation: stream a multi-MB document and assert the live register
    # footprint stays small (KB), i.e. genuinely O(1) in input length. (The committed
    # 100 MiB xlarge fixture is gitignored and too slow for a unit test; a generated
    # ~8 MiB document of bounded blocks proves the same property.)
    block = b"<p>A paragraph of moderate length used to fill the document.</p>"
    html = block * (8 * 1024 * 1024 // len(block))  # ~8 MiB
    assert len(html) > 7_000_000
    peak = _peak_footprint(html)
    assert peak < 128_000, peak  # ~KB-scale, independent of the multi-MB input


@pytest.mark.skipif(not _XLARGE.exists(), reason="xlarge fixture is gitignored/optional")
def test_xlarge_fixture_streams_in_bounded_memory() -> None:
    # Fixture-backed validation against the real ~100 MiB document when present: peak
    # live register memory must be a tiny fraction of the input (sub-linear ⇒ O(1)).
    data = _XLARGE.read_bytes()
    peak = _peak_footprint(data, chunk=64 * 1024)
    assert peak < len(data) // 20, (peak, len(data))


def test_nesting_depth_bounds_footprint_not_length() -> None:
    # A long flat document and a short deep one: footprint tracks DEPTH, not length.
    flat = b"<p>x</p>" * 5_000
    deep = b"<div>" * 40 + b"<p>x</p>" + b"</div>" * 40
    assert _peak_footprint(flat) < 64_000
    assert _peak_footprint(deep) < 64_000


def test_single_giant_block_is_the_documented_exception() -> None:
    # The one way to inflate the bound is a single huge open block (design §4.7 worst
    # case): O(largest open block), still not O(whole document) when blocks are bounded.
    giant = b"<p>" + (b"word " * 200_000) + b"</p>"
    assert _peak_footprint(giant) > 100_000  # the open <p> register holds its content
    # ...but a document of many SMALL blocks of the same total size stays bounded:
    assert _peak_footprint(b"<p>word</p>" * 100_000) < 64_000


def test_table_reservoir_bounded_by_table_not_document() -> None:
    # The table buffer is the localized bounded register-array (design §11): a table is
    # buffered until </table>, bounded by the table's own size, independent of how much
    # document precedes it.
    table = b"<table>" + b"<tr><td>a</td><td>b</td></tr>" * 50 + b"</table>"
    peak_with_prefix = _peak_footprint(b"<p>x</p>" * 10_000 + table)
    peak_table_only = _peak_footprint(table)
    assert peak_with_prefix < peak_table_only + 64_000


def test_text_coalescing_buffer_is_released() -> None:
    # The coalescing buffer holds at most one text node and is flushed on the next
    # non-data event, so it does not accumulate across a long run of text+element pairs.
    assert _peak_footprint(b"text<span>x</span>" * 5_000) < 64_000


def test_options_does_not_change_invariant() -> None:
    assert _peak_footprint(b"<p>block</p>" * 5_000, chunk=64 * 1024) < 128_000
    # explicit non-default chunk_size option is just feed granularity, same bound
    driver = IncrementalDriver(Options(chunk_size=8))
    html = b"<p>block</p>" * 2_000
    peak = 0
    for i in range(0, len(html), 4096):
        driver.feed(html[i:i + 4096])
        peak = max(peak, register_footprint(driver.emitter))
        driver.drain()
    driver.close()
    assert peak < 64_000
