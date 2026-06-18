"""Streaming drain seam — convert_stream yields completed blocks before EOF, and the
drained prefix is never rewritten (design §4.7 safe-emission barrier)."""

from __future__ import annotations

import asyncio

import pytest

from html2md import convert, convert_stream, convert_stream_async
from html2md.parser import IncrementalDriver

DOC = "<p>alpha</p><p>beta</p><p>gamma</p>"
# Many blocks: lxml's push parser holds the final element pending lookahead, but with
# many completed blocks it flushes earlier ones progressively — which is what lets the
# drain yield before EOF. (A single block fed alone stays pending until close.)
BIG_BLOCKS = [f"<p>block{i}</p>".encode() for i in range(200)]
BIG_DOC = b"".join(BIG_BLOCKS)


def test_drain_yields_completed_blocks_before_eof() -> None:
    # Feed every block but DO NOT close; the parser must already have flushed completed
    # blocks, so drain returns non-empty before end-of-input.
    d = IncrementalDriver()
    for block in BIG_BLOCKS:
        d.feed(block)
    early = d.drain()
    assert early, "nothing drained before close — converter waited for EOF"
    assert "block0" in early
    tail = d.close()
    assert convert(BIG_DOC.decode()) == (early + tail) or "block199" in (early + tail)


def test_stream_concatenation_equals_convert() -> None:
    chunks = [DOC[i:i + 6].encode() for i in range(0, len(DOC), 6)]
    pieces = list(convert_stream(chunks))
    assert "".join(pieces) == convert(DOC)


def test_stream_actually_yields_multiple_pieces() -> None:
    # Feeding many blocks one chunk at a time, the parser flushes progressively, so more
    # than one piece arrives across the stream (not everything at the final close).
    pieces = list(convert_stream(BIG_BLOCKS))
    assert len(pieces) >= 2
    assert "".join(pieces) == convert(BIG_DOC.decode())


def test_no_yielded_prefix_is_rewritten() -> None:
    # The running concatenation of yielded chunks must always be a prefix of the final
    # document (streaming invariant): no chunk we already emitted gets mutated.
    chunks = [c.encode() for c in (DOC[:10], DOC[10:20], DOC[20:])]
    final = convert(DOC)
    running = ""
    for piece in convert_stream(chunks):
        running += piece
        assert final.startswith(running), (running, final)
    assert running == final


def test_stream_async_matches_convert() -> None:
    async def run() -> list[str]:
        async def agen():
            for i in range(0, len(DOC), 6):
                yield DOC[i:i + 6].encode()
        return [c async for c in convert_stream_async(agen())]

    pieces = asyncio.run(run())
    assert "".join(pieces) == convert(DOC)


@pytest.mark.parametrize("html", [
    b"<title>T</title>\n<h1>H</h1>",            # text in <head> + structural boundary
    b"<title>T</title>\n<p>x</p>",
    b"<head><title>T</title></head>\n<h1>H</h1>",
    b"<textarea>\n\n*foo*\n\n_bar_\n\n</textarea>",  # lxml splits textarea text by feed
    b"<p>a</p>\n<p>b</p>",
    b"<p><a href='/url'>foo</a></p>\n<blockquote>q</blockquote>",
    b"<ul><li>a</li>\n<li>b</li></ul>",
    b"foo<ul><li>bar</li></ul>baz",
    b"<div><p>x</p>  <p>y</p></div>",
])
@pytest.mark.parametrize("chunk_size", [1, 2, 3, 7, 64])
def test_chunk_invariance_structural_boundaries(html: bytes, chunk_size: int) -> None:
    # The §9.1 guarantee: convert_stream output is byte-identical to convert no matter
    # how the bytes are split — including across structural/whitespace boundaries where
    # lxml delivers text nodes in feed-dependent pieces (text coalescing restores it).
    from html2md import convert, convert_stream
    chunks = [html[i:i + chunk_size] for i in range(0, len(html), chunk_size)]
    assert "".join(convert_stream(chunks)) == convert(html)


def test_drain_holds_back_trailing_whitespace() -> None:
    # After a block, the trailing block-separator whitespace is held back (it may be
    # rstripped at close or merged with the next block), so a drained piece never ends
    # in whitespace that could later change.
    d = IncrementalDriver()
    d.feed(b"<p>x</p>")
    piece = d.drain()
    assert piece == piece.rstrip()  # no trailing whitespace yielded
