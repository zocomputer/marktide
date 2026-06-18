"""Black-box end-to-end tests (test-plan §1) — drive the real public API on real-world
HTML and assert robustness + cross-entry-point equivalence. No internals are imported.

What it covers:
- no crash, valid non-empty Markdown on real documents;
- ``convert`` ≡ ``convert_stream`` byte-for-byte on real docs;
- the async paths (``convert_async`` / ``convert_stream_async``) yield and agree with sync;
- ``huge_tree`` keeps a >10 MB single text node from being truncated (design §4.1);
- the 110 MiB ``xlarge`` fixture converts without truncation (proportional output).

Runner / CI placement
---------------------
- ``pytest tests/e2e``               → PR CI: always-on inline + huge_tree checks, plus the
  ``small`` (100 KiB) and ``medium`` (5 MiB) benchmark fixtures when present.
- ``pytest tests/e2e --run-nightly`` → nightly / on-demand: adds ``large`` (50 MiB) and
  ``xlarge`` (110 MiB).
(Suggested make targets: ``make e2e`` and ``make e2e-full`` once a Makefile exists.)

The real fixtures are the locally-generated, gitignored benchmark corpus
(``benchmarks/fixtures/*.html`` via ``scripts/regenerate_benchmark_fixtures.py``); a test is
skipped if its fixture is absent, so the suite still runs (inline + huge_tree) without them.
Artifact: JUnit XML from the CI runner.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

from html2md import convert, convert_async, convert_stream, convert_stream_async

_FIXTURES = Path(__file__).resolve().parents[2] / "benchmarks" / "fixtures"

# A small, feature-rich document committed inline so the suite always has signal even when
# the generated benchmark fixtures are absent (headings, inline marks, links, lists,
# blockquote, pre/code, image, a dropped <style>, and a table).
_INLINE_DOC = (
    "<!doctype html><html><head><title>t</title><style>.x{color:red}</style></head>"
    "<body>"
    "<h1>Title</h1>"
    "<p>A paragraph with <strong>bold</strong>, <em>em</em>, <code>code()</code>, "
    'and a <a href="https://example.com" title="ex">link</a>.</p>'
    "<h2>List</h2>"
    "<ul><li>one</li><li>two<ul><li>nested</li></ul></li></ul>"
    "<blockquote><p>quote</p></blockquote>"
    "<pre><code>x = 1\n</code></pre>"
    '<p>Image: <img src="/i.png" alt="alt"></p>'
    "<table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table>"
    "</body></html>"
)


def _chunks(data: bytes, size: int = 64 * 1024) -> Iterator[bytes]:
    for i in range(0, len(data), size):
        yield data[i : i + size]


def _load(name: str) -> bytes:
    path = _FIXTURES / f"{name}.html"
    if not path.exists():
        pytest.skip(
            f"benchmark fixture {name}.html absent — run scripts/regenerate_benchmark_fixtures.py"
        )
    return path.read_bytes()


# Small chunk sizes force real feed() boundaries on the committed inline doc, so PR CI always
# exercises chunk-invariance without depending on the gitignored benchmark fixtures.
_BOUNDARY_SIZES = (1, 7, 17, 256)


async def _collect_stream_async(data: bytes, size: int = 64 * 1024) -> str:
    async def _agen() -> AsyncIterator[bytes]:
        for chunk in _chunks(data, size):
            yield chunk

    return "".join([part async for part in convert_stream_async(_agen())])


# --- always-on: the inline document --------------------------------------------

def test_inline_doc_converts_to_nonempty_markdown() -> None:
    md = convert(_INLINE_DOC)
    assert isinstance(md, str) and md.strip()
    # default markdownify-compatible rendering: setext h1, asterisk emphasis, inline link
    assert "Title\n=====" in md
    assert "**bold**" in md
    assert "[link](https://example.com" in md
    # dropped <style> leaves no residue in the output
    assert "color:red" not in md


def test_inline_async_matches_sync() -> None:
    assert asyncio.run(convert_async(_INLINE_DOC)) == convert(_INLINE_DOC)


@pytest.mark.parametrize("size", _BOUNDARY_SIZES)
def test_inline_convert_equals_stream_at_boundaries(size: int) -> None:
    # multi-chunk on the committed doc: real feed() boundaries in default PR CI
    whole = convert(_INLINE_DOC)
    streamed = "".join(convert_stream(_chunks(_INLINE_DOC.encode(), size)))
    assert streamed == whole


@pytest.mark.parametrize("size", _BOUNDARY_SIZES)
def test_inline_convert_stream_async_at_boundaries(size: int) -> None:
    whole = convert(_INLINE_DOC)
    streamed = asyncio.run(_collect_stream_async(_INLINE_DOC.encode(), size))
    assert streamed == whole


def test_huge_tree_no_truncation_on_large_text_node() -> None:
    # A single text node well past libxml2's default 10 MB XML_MAX_TEXT_LENGTH. Without
    # huge_tree=True the node is truncated/dropped; the driver sets it unconditionally
    # (design §4.1), so the tail sentinel must survive a ~12 MB conversion.
    filler = "lorem ipsum " * 1_000_000
    sentinel = "ZSENTINELZ-END-MARKER"
    md = convert("<p>" + filler + sentinel + "</p>")
    assert sentinel in md
    assert len(md) > 10_000_000


# --- real benchmark fixtures: small/medium default, large/xlarge nightly --------

@pytest.mark.parametrize("name", ["small", "medium"])
def test_real_fixture_no_crash_valid_markdown(name: str) -> None:
    md = convert(_load(name))
    assert isinstance(md, str) and md.strip()
    assert len(md) > 1000  # proportional output, not silently truncated to a tiny cap


@pytest.mark.parametrize("name", ["small", "medium"])
def test_real_fixture_convert_equals_stream(name: str) -> None:
    data = _load(name)
    assert convert(data) == "".join(convert_stream(_chunks(data)))


@pytest.mark.parametrize("name", ["small", "medium"])
def test_real_fixture_async_matches_sync(name: str) -> None:
    data = _load(name)
    whole = convert(data)
    assert asyncio.run(convert_async(data)) == whole


@pytest.mark.nightly
@pytest.mark.parametrize("name", ["large", "xlarge"])
def test_large_fixture_no_truncation(name: str) -> None:
    data = _load(name)
    md = convert(data)
    assert isinstance(md, str) and md.strip()
    # no truncation: output is a large fraction of the input, not capped short
    assert len(md) > len(data) // 10


@pytest.mark.nightly
def test_xlarge_convert_equals_stream() -> None:
    data = _load("xlarge")
    assert convert(data) == "".join(convert_stream(_chunks(data)))


@pytest.mark.nightly
def test_xlarge_async_matches_sync() -> None:
    data = _load("xlarge")
    assert asyncio.run(convert_async(data)) == convert(data)
