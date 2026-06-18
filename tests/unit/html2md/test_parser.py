"""IncrementalDriver — feed loop, close/cleanup, huge_tree no-truncation."""

from __future__ import annotations

import pytest

from html2md.options import Options
from html2md.parser import IncrementalDriver


def test_feed_all_then_close_returns_markdown() -> None:
    with IncrementalDriver() as d:
        d.feed_all(b"<strong>hi</strong>")
        assert d.close() == "**hi**"


def test_close_is_idempotent() -> None:
    d = IncrementalDriver()
    d.feed_all(b"<span>x</span>")
    first = d.close()
    assert d.close() == first  # second close returns cached result, no error


def test_feed_after_close_raises() -> None:
    d = IncrementalDriver()
    d.feed_all(b"<p>x</p>")
    d.close()
    with pytest.raises(RuntimeError, match="feed after close"):
        d.feed(b"<p>more</p>")


def test_context_manager_closes_on_exception() -> None:
    d = IncrementalDriver()
    with pytest.raises(ValueError):
        with d:
            d.feed(b"<p>partial")
            raise ValueError("boom")
    # parser released: a subsequent feed is rejected because close() ran in __exit__.
    with pytest.raises(RuntimeError):
        d.feed(b"<p>x</p>")


def test_feed_in_tiny_chunks_matches_whole() -> None:
    html = b"<div><strong>a</strong><span>b</span><hr></div>"
    with IncrementalDriver() as whole:
        whole.feed(html)
        whole_out = whole.close()
    with IncrementalDriver() as split:
        for i in range(len(html)):
            split.feed(html[i:i + 1])
        split_out = split.close()
    assert whole_out == split_out  # chunk-invariance at the driver level


def test_huge_tree_prevents_truncation() -> None:
    # libxml2 silently truncates a text node past its internal limit (~10 MB) unless
    # huge_tree=True, which the driver sets unconditionally. An 11 MB text node must
    # survive intact. (The full xlarge round-trip guard lives in the integration tests.)
    n = 11_000_000
    html = b"<p>" + (b"Z" * n) + b"</p>"
    with IncrementalDriver() as d:
        d.feed_all(html)
        out = d.close()
    assert out.count("Z") == n


def test_chunk_size_option_controls_feed_granularity() -> None:
    # Smaller chunk_size must not change output (only feed cadence).
    html = b"<strong>x</strong>" * 100
    a = IncrementalDriver(Options(chunk_size=8))
    a.feed_all(html)
    b = IncrementalDriver(Options(chunk_size=64 * 1024))
    b.feed_all(html)
    assert a.close() == b.close()
