"""Rule dispatch contract — handlers, registration, and the TagHandler protocol."""

from __future__ import annotations

from html2md.emitter import MarkdownEmitter
from html2md.rules import TAG_HANDLERS, PrefixSuffixHandler, TransparentHandler
from html2md.rules.base import TagHandler


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
    # Replicate the emitter's end() routing: children render into the frame buffer,
    # the frame is popped, then the handler wraps em.content into the parent buffer.
    h = PrefixSuffixHandler("<", ">")
    em = MarkdownEmitter()
    em.start("x", {})            # unregistered tag → frame pushed, no handler
    em.data("body")             # accumulates into the frame buffer
    frame = em.state.pop()
    em._content = "".join(frame.content)
    h.end(em)                   # emits prefix + content + suffix to the (root) parent
    assert "".join(em.root) == "<body>"


def test_transparent_passes_children_through() -> None:
    assert _run("div", "abc") == "abc"


def test_hr_is_registered_as_local_block() -> None:
    assert "hr" in TAG_HANDLERS
    em = MarkdownEmitter()
    em.start("hr", {})
    em.end("hr")
    assert em.close() == "---"  # document strip removes the surrounding blank lines


def test_structural_tags_registered_transparent() -> None:
    for tag in ("div", "section", "article", "span", "main"):
        assert isinstance(TAG_HANDLERS[tag], TransparentHandler)
