"""Chunk-boundary invariance scaffold for the streaming HTML→Markdown API.

Design invariant: for every input byte string, every partition must satisfy
``"".join(convert_stream(partition)) == convert(whole)`` byte-for-byte.

These tests intentionally import the future public API described in docs/design.md
§6.1 and skip until ``src/marktide`` exists. The split-point machinery is live now
and reuses the staged conformance corpus from ``tests.conformance.differential``.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from collections.abc import Iterable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFORMANCE_DIR = REPO_ROOT / "tests" / "conformance"
if str(CONFORMANCE_DIR) not in sys.path:
    sys.path.insert(0, str(CONFORMANCE_DIR))

from differential import Case, load_cases  # noqa: E402  # ty: ignore[unresolved-import]

FIXED_CHUNK_SIZES = (1, 7, 64, 4096)
MAX_ADVERSARIAL_OFFSETS_PER_CASE = 96


def _load_marktide_api():
    try:
        module = importlib.import_module("marktide")
    except ModuleNotFoundError:
        pytest.skip("marktide public API is not implemented yet")
    missing = [name for name in ("convert", "convert_stream") if not hasattr(module, name)]
    if missing:
        pytest.skip(f"marktide public API missing: {', '.join(missing)}")
    return module.convert, module.convert_stream


def split_bytes(payload: bytes, offsets: Iterable[int]) -> list[bytes]:
    """Partition ``payload`` at sorted unique byte offsets."""

    cleaned = sorted({offset for offset in offsets if 0 < offset < len(payload)})
    chunks: list[bytes] = []
    previous = 0
    for offset in cleaned:
        chunks.append(payload[previous:offset])
        previous = offset
    chunks.append(payload[previous:])
    return chunks


def fixed_chunk_offsets(payload: bytes, chunk_size: int) -> list[int]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    return list(range(chunk_size, len(payload), chunk_size))


STRUCTURAL_BOUNDARY_REPRO_CASES = (
    b"<title>T</title>\n<h1>H</h1>",
    b"<title>T</title>\n<p>x</p>",
    b"<head><title>T</title></head>\n<h1>H</h1>",
)

STRUCTURAL_BOUNDARY_CONTROL_CASES = (
    b"<title>T</title><h1>H</h1>",
    b"<html><head><title>T</title></head><body>\n<h1>H</h1></body></html>",
    b"<meta charset='utf-8'>\n<h1>H</h1>",
    b"<!-- c -->\n<h1>H</h1>",
    b"text\n<h1>H</h1>",
    b"<style>x</style>\n<h1>H</h1>",
    b"<h1>A</h1>\n<h1>B</h1>",
)


def _assert_stream_matches_convert_for_offsets(payload: bytes, offsets: Iterable[int]):
    convert, convert_stream = _load_marktide_api()
    chunks = split_bytes(payload, offsets)

    assert "".join(convert_stream(chunks)) == convert(payload)


def structural_boundary_offsets(payload: bytes) -> list[int]:
    """Split around adjacent structural tags/wrapper-sensitive boundaries."""

    offsets: set[int] = set()
    boundary_patterns = [
        rb"><",
        rb">\s+<",
        rb"</title>\s*<h1\b",
        rb"</head>\s*<body\b",
        rb"</body>\s*</html>",
    ]
    for pattern in boundary_patterns:
        for match in re.finditer(pattern, payload, re.I | re.S):
            start, end = match.span()
            offsets.update(range(max(1, start - 2), min(len(payload), end + 3)))
    return _dedupe_cap(offsets, len(payload), MAX_ADVERSARIAL_OFFSETS_PER_CASE)


def adversarial_split_offsets(payload: bytes) -> list[int]:
    """Find split points inside parser-sensitive constructs.

    Bias points land inside tags, attributes, entities, comments, pre/code text,
    table rows/cells, nested list items, whitespace runs, and UTF-8 multibyte
    sequences. The list is deterministic and capped so every conformance case can
    run in CI without exploding the partition count.
    """

    offsets: list[int] = []
    offsets.extend(_inside_regex(payload, rb"<[A-Za-z][^>]{1,240}>", fractions=(0.25, 0.5, 0.75)))
    offsets.extend(_inside_regex(payload, rb"\s[A-Za-z_:][-A-Za-z0-9_:.]*\s*=\s*(['\"]).{1,240}?\1", fractions=(0.5,)))
    offsets.extend(_inside_regex(payload, rb"&[#A-Za-z0-9][A-Za-z0-9#xX]*;", fractions=(0.5,)))
    offsets.extend(_inside_regex(payload, rb"<!--.*?-->", flags=re.S, fractions=(0.25, 0.5, 0.75)))
    offsets.extend(_inside_tag_body(payload, b"pre"))
    offsets.extend(_inside_tag_body(payload, b"code"))
    offsets.extend(_inside_regex(payload, rb"<tr\b[^>]*>.*?</tr>", flags=re.I | re.S, fractions=(0.33, 0.66)))
    offsets.extend(_inside_regex(payload, rb"<li\b[^>]*>.*?</li>", flags=re.I | re.S, fractions=(0.33, 0.66)))
    offsets.extend(_inside_regex(payload, rb"\s{2,}", fractions=(0.5,)))
    offsets.extend(structural_boundary_offsets(payload))
    offsets.extend(_inside_utf8_sequences(payload))
    offsets.extend([1, max(1, len(payload) - 1)])
    return _dedupe_cap(offsets, len(payload), MAX_ADVERSARIAL_OFFSETS_PER_CASE)


def _inside_regex(payload: bytes, pattern: bytes, *, flags: int = 0, fractions: tuple[float, ...]) -> list[int]:
    offsets: list[int] = []
    for match in re.finditer(pattern, payload, flags):
        start, end = match.span()
        width = end - start
        if width <= 1:
            continue
        for fraction in fractions:
            offsets.append(start + max(1, min(width - 1, int(width * fraction))))
    return offsets


def _inside_tag_body(payload: bytes, tag: bytes) -> list[int]:
    pattern = rb"<" + tag + rb"\b[^>]*>.*?</" + tag + rb">"
    return _inside_regex(payload, pattern, flags=re.I | re.S, fractions=(0.33, 0.66))


def _inside_utf8_sequences(payload: bytes) -> list[int]:
    offsets: list[int] = []
    index = 0
    while index < len(payload):
        byte = payload[index]
        if 0xC2 <= byte <= 0xDF and index + 1 < len(payload):
            offsets.append(index + 1)
            index += 2
        elif 0xE0 <= byte <= 0xEF and index + 2 < len(payload):
            offsets.extend([index + 1, index + 2])
            index += 3
        elif 0xF0 <= byte <= 0xF4 and index + 3 < len(payload):
            offsets.extend([index + 1, index + 2, index + 3])
            index += 4
        else:
            index += 1
    return offsets


def _dedupe_cap(offsets: Iterable[int], payload_len: int, cap: int) -> list[int]:
    unique = sorted({offset for offset in offsets if 0 < offset < payload_len})
    if len(unique) <= cap:
        return unique
    # Keep coverage across the whole input rather than only early constructs.
    return [unique[round(i * (len(unique) - 1) / (cap - 1))] for i in range(cap)]


def conformance_cases() -> list[Case]:
    if importlib.util.find_spec("marktide") is None:
        return [Case(id="marktide-api-not-implemented", layer="scaffold", source_path="inline", html="<p>skip</p>")]
    fixture_root = CONFORMANCE_DIR / "fixtures"
    if not fixture_root.exists():
        return [
            Case(
                id="conformance-fixtures-not-generated",
                layer="scaffold",
                source_path="inline",
                html="<p>skip</p>",
                metadata={"skip_reason": "conformance fixtures are not generated; run scripts/regenerate_conformance_corpus.py"},
            )
        ]
    return load_cases(fixture_root)


@pytest.mark.parametrize("case", conformance_cases(), ids=lambda case: case.id)
def test_convert_stream_matches_convert_for_adversarial_splits(case: Case):
    if skip_reason := case.metadata.get("skip_reason"):
        pytest.skip(str(skip_reason))
    convert, convert_stream = _load_marktide_api()
    payload = case.html.encode("utf-8", errors="replace")
    offsets = adversarial_split_offsets(payload)
    chunks = split_bytes(payload, offsets)

    assert "".join(convert_stream(chunks)) == convert(payload)


@pytest.mark.parametrize("chunk_size", FIXED_CHUNK_SIZES)
def test_convert_stream_matches_convert_for_fixed_chunk_sweep(chunk_size: int):
    convert, convert_stream = _load_marktide_api()
    # A compact synthetic fixture exercises the constructs called out in the
    # design without making the fixed 1-byte sweep expensive in every PR.
    payload = SYNTHETIC_ADVERSARIAL_HTML
    chunks = split_bytes(payload, fixed_chunk_offsets(payload, chunk_size))

    assert "".join(convert_stream(chunks)) == convert(payload)



@pytest.mark.parametrize("payload", STRUCTURAL_BOUNDARY_REPRO_CASES)
def test_convert_stream_matches_convert_for_implicit_head_body_structural_boundaries(payload: bytes):
    # Regression for zo-1fp.19: streaming flushes around structural/document
    # wrapper boundaries must exactly match whole-document conversion. The bug
    # appears when a <title> closes, a source newline follows, and lxml has to
    # infer the head/body boundary because the input lacks an explicit wrapper.
    _assert_stream_matches_convert_for_offsets(payload, range(1, len(payload)))


@pytest.mark.parametrize("payload", STRUCTURAL_BOUNDARY_CONTROL_CASES)
def test_convert_stream_matches_convert_for_structural_boundary_controls(payload: bytes):
    # These nearby shapes should remain covered as controls so the repro test is
    # targeted at implicit <title> + newline + body-block tree construction, not
    # every structural boundary.
    _assert_stream_matches_convert_for_offsets(payload, range(1, len(payload)))


def test_structural_boundary_offsets_cover_title_h1_transition():
    payload = STRUCTURAL_BOUNDARY_REPRO_CASES[0]
    offsets = structural_boundary_offsets(payload)
    assert offsets
    chunks = split_bytes(payload, offsets)
    assert b"".join(chunks) == payload
    boundary = payload.index(b"<h1")
    assert any(boundary - 2 <= offset <= boundary + 2 for offset in offsets)


SYNTHETIC_ADVERSARIAL_HTML = """\
<!doctype html><html><body>
<!-- comment with <tag> and &amp; -->
<section data-long-attr="alpha &amp; beta gamma">
  <h1>Title &amp; entity</h1>
  <p>Unicode: café ☕ — split multibyte here.</p>
  <pre><code>if (a &lt; b) { return "x"; }</code></pre>
  <table><tbody><tr><td>left</td><td>right &amp; entity</td></tr></tbody></table>
  <ul><li>outer<ul><li>inner &amp; nested</li></ul></li></ul>
</section>
</body></html>
""".encode("utf-8")


def test_adversarial_offsets_hit_expected_constructs():
    offsets = adversarial_split_offsets(SYNTHETIC_ADVERSARIAL_HTML)
    assert offsets == sorted(set(offsets))
    assert all(0 < offset < len(SYNTHETIC_ADVERSARIAL_HTML) for offset in offsets)
    assert len(offsets) >= 20
    chunks = split_bytes(SYNTHETIC_ADVERSARIAL_HTML, offsets)
    assert b"".join(chunks) == SYNTHETIC_ADVERSARIAL_HTML


def test_fixed_chunk_offsets_partition_payload():
    payload = b"abcdefghi"
    assert fixed_chunk_offsets(payload, 3) == [3, 6]
    assert split_bytes(payload, [3, 6]) == [b"abc", b"def", b"ghi"]
