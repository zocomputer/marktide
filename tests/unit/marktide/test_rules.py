"""Rule dispatch contract — handlers, registration, and the TagHandler protocol."""

from __future__ import annotations

from marktide.emitter import MarkdownEmitter
from marktide.rules import TAG_HANDLERS, PrefixSuffixHandler, TransparentHandler
from marktide.rules.base import TagHandler


def _run(handler_tag: str, children: str) -> str:
    em = MarkdownEmitter()
    em.start(handler_tag, {})
    em.data(children)
    em.end(handler_tag)
    return em.close()


def test_registered_handlers_satisfy_protocol() -> None:
    assert TAG_HANDLERS, "dispatch table is empty"
    for tag, handler in TAG_HANDLERS.items():
        assert isinstance(handler, TagHandler), f"{tag!r} handler violates protocol"


def test_prefix_suffix_wraps_rendered_children() -> None:
    # Drive the real emitter flow: a buffering handler accumulates its children, then
    # wraps em.content in prefix/suffix into the parent buffer at end.
    em = MarkdownEmitter()
    em._handlers = {**TAG_HANDLERS, "x": PrefixSuffixHandler("<", ">")}
    em.start("x", {})
    em.data("body")
    em.end("x")
    assert em.close() == "<body>"


def test_transparent_passes_children_through() -> None:
    assert _run("div", "abc") == "abc"


def test_hr_is_registered_as_local_block() -> None:
    assert "hr" in TAG_HANDLERS
    em = MarkdownEmitter()
    em.start("hr", {})
    em.end("hr")
    assert em.close() == "---"  # document strip removes the surrounding blank lines


def test_structural_tags_registered_transparent() -> None:
    # Tags with no markdownify converter pass children through unchanged.
    # (div/section/article are NOT here — markdownify's convert_div makes them blocks.)
    for tag in ("span", "main", "header", "footer", "nav", "aside", "figure"):
        assert isinstance(TAG_HANDLERS[tag], TransparentHandler)
