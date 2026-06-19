"""MarkdownEmitter — dispatch, the buffer/content model, escaping, tag filters."""

from __future__ import annotations


from marktide.emitter import MarkdownEmitter
from marktide.options import Options


def _emit(html_events) -> str:
    """Drive a sequence of (kind, *args) SAX events through a fresh emitter."""
    em = MarkdownEmitter()
    for kind, *args in html_events:
        getattr(em, kind)(*args)
    return em.close()


def test_transparent_passthrough_and_inline_wrap() -> None:
    out = _emit([
        ("start", "div", {}),
        ("data", "Hello "),
        ("start", "strong", {}),
        ("data", "world"),
        ("end", "strong"),
        ("end", "div"),
    ])
    assert out == "Hello **world**"


def test_content_is_rendered_children_at_end() -> None:
    # A handler reads em.content (markdownify's `text`) — strong wraps its children.
    out = _emit([
        ("start", "strong", {}),
        ("start", "span", {}),
        ("data", "x"),
        ("end", "span"),
        ("end", "strong"),
    ])
    assert out == "**x**"


def test_escaping_applies_per_options() -> None:
    em = MarkdownEmitter()  # defaults: escape_asterisks + escape_underscores on
    em.start("span", {})
    em.data("a*b_c")
    em.end("span")
    assert em.close() == "a\\*b\\_c"


def test_escape_disabled() -> None:
    em = MarkdownEmitter(Options(escape_asterisks=False, escape_underscores=False))
    em.start("span", {})
    em.data("a*b_c")
    em.end("span")
    assert em.close() == "a*b_c"


def test_comment_is_dropped() -> None:
    out = _emit([("data", "a"), ("comment", "ignore me"), ("data", "b")])
    assert out == "ab"


def test_document_strip_default() -> None:
    out = _emit([("data", "  \n trimmed \n  ")])
    assert out == "trimmed"


def test_strip_filter_emits_children_only() -> None:
    em = MarkdownEmitter(Options(strip=("strong",)))
    for kind, *args in [
        ("start", "strong", {}), ("data", "kept"), ("end", "strong"),
    ]:
        getattr(em, kind)(*args)
    assert em.close() == "kept"  # no ** wrapping because strong is stripped


def test_convert_allowlist_skips_unlisted_tags() -> None:
    em = MarkdownEmitter(Options(convert=("strong",)))
    for kind, *args in [
        ("start", "strong", {}), ("data", "a"), ("end", "strong"),
        ("start", "hr", {}), ("end", "hr"),  # hr not in allowlist → no rule
    ]:
        getattr(em, kind)(*args)
    assert em.close() == "**a**"


def test_unknown_tag_passes_text_through() -> None:
    out = _emit([("start", "custom-el", {}), ("data", "z"), ("end", "custom-el")])
    assert out == "z"


def test_tag_names_are_lowercased() -> None:
    out = _emit([("start", "STRONG", {}), ("data", "x"), ("end", "STRONG")])
    assert out == "**x**"


def test_implements_target_protocol() -> None:
    em = MarkdownEmitter()
    for method in ("start", "end", "data", "comment", "close"):
        assert callable(getattr(em, method))


def test_inline_element_trailing_space_preserved_before_text_sibling() -> None:
    # An inline element whose text ends in a space, immediately followed by a
    # non-whitespace text sibling: the deferred trailing whitespace must survive
    # the inline close so the words stay separated. Regression for the real-world
    # "<a>Hourly <span>Weather </span>Forecast</a>" collapsing to "WeatherForecast".
    out = _emit([
        ("start", "div", {}),
        ("data", "Hourly "),
        ("start", "span", {}),
        ("data", "Weather "),
        ("end", "span"),
        ("data", "Forecast"),
        ("end", "div"),
    ])
    assert out == "Hourly Weather Forecast"
