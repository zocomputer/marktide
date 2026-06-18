"""Regression: handlers read their OWN per-element attrs/data at end() via em.frame,
even for nested same-tag elements (the frame is popped before end(), so em.state.top
is the parent — em.frame is the just-closed element)."""

from __future__ import annotations

from collections.abc import Mapping

from html2md.emitter import MarkdownEmitter
from html2md.rules import TAG_HANDLERS


class _LinkLike:
    """Reads em.frame.attrs at end (attribute-only handler, no start)."""

    def start(self, em: MarkdownEmitter, attrs: Mapping[str, str]) -> None:
        return None

    def end(self, em: MarkdownEmitter) -> None:
        href = em.frame.attrs.get("href", "")
        em.emit(f"[{em.content}]({href})")


class _Stashing:
    """Stashes per-element data at start, reads it back at end via em.frame.data."""

    def start(self, em: MarkdownEmitter, attrs: Mapping[str, str]) -> None:
        em.state.top.data["id"] = attrs.get("id", "")

    def end(self, em: MarkdownEmitter) -> None:
        em.emit(f"<{em.frame.data['id']}>{em.content}</{em.frame.data['id']}>")


def _emitter_with(tag: str, handler: object) -> MarkdownEmitter:
    em = MarkdownEmitter()
    em._handlers = {**TAG_HANDLERS, tag: handler}
    return em


def test_nested_same_tag_reads_distinct_attrs() -> None:
    em = _emitter_with("a", _LinkLike())
    em.start("a", {"href": "1"})
    em.start("a", {"href": "2"})
    em.data("x")
    em.end("a")   # inner: [x](2)
    em.end("a")   # outer wraps inner: [[x](2)](1)
    assert em.close() == "[[x](2)](1)"


def test_nested_same_tag_reads_distinct_stashed_data() -> None:
    em = _emitter_with("ul", _Stashing())
    em.start("ul", {"id": "outer"})
    em.start("ul", {"id": "inner"})
    em.data("leaf")
    em.end("ul")  # <inner>leaf</inner>
    em.end("ul")  # <outer><inner>leaf</inner></outer>
    assert em.close() == "<outer><inner>leaf</inner></outer>"


def test_frame_is_the_element_being_ended_not_the_parent() -> None:
    seen: list[tuple[str, str | None]] = []

    class _Recorder:
        def start(self, em: MarkdownEmitter, attrs: Mapping[str, str]) -> None:
            return None

        def end(self, em: MarkdownEmitter) -> None:
            parent = em.state.top.tag if em.state.top else None
            seen.append((em.frame.attrs.get("id", ""), parent))

    em = _emitter_with("a", _Recorder())
    em.start("a", {"id": "outer"})
    em.start("a", {"id": "inner"})
    em.end("a")
    em.end("a")
    # inner ends first: its frame id is "inner", parent on the stack is "outer".
    assert seen == [("inner", "a"), ("outer", None)]


def test_frame_is_none_outside_end() -> None:
    em = MarkdownEmitter()
    assert em.frame is None
    em.start("div", {})
    assert em.frame is None  # not inside a handler's end
