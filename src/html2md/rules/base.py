"""The tag-handler dispatch contract.

This is the seam the per-tag rule modules build against (block/inline rules and table
rules are added separately). A *handler* converts one HTML tag to Markdown by reacting
to the element's SAX ``start`` and ``end`` events. The emitter pushes/pops the element on the state
stack and routes the events to the registered handler.

Contract
--------
A handler is any object implementing :class:`TagHandler`::

    class TagHandler(Protocol):
        def start(self, em: MarkdownEmitter, attrs: Mapping[str, str]) -> None: ...
        def end(self, em: MarkdownEmitter) -> None: ...

* ``start`` is called *after* the element's :class:`~html2md.state.Frame` is pushed,
  so ``em.state.top`` is this element. Use it to mutate state (e.g. ``pre_depth``, list
  context) or capture attributes for ``end`` (e.g. a link href onto ``em.state.top.data``).
  ``start`` normally emits nothing — output is produced at ``end`` from the rendered
  children.
* ``end`` is called *after* the frame is popped. The element's fully rendered child
  Markdown is available as ``em.content`` (markdownify's ``text`` argument). The handler
  emits the element's final Markdown via ``em.emit(...)``, which lands in the parent's
  buffer — typically ``em.emit(prefix + em.content + suffix)``, but the handler may
  read/transform the content (setext underline length, code-fence sizing, dropping an
  empty element).
* Text content arrives via the emitter's ``data``→``emit_text`` path, which escapes per
  ``Options`` centrally, so ``em.content`` is already-escaped — handlers do **not**
  re-escape it. ``em.emit`` writes raw (handler-produced) Markdown; ``em.escape`` is for
  the rare string a handler sources itself (e.g. link text from an ``alt`` attribute).

Most tags are **local** — wrap the children in a fixed prefix/suffix — and use
:class:`PrefixSuffixHandler`. Non-local constructs (links need the href, lists need
nesting depth, tables buffer until ``</table>``) implement custom handlers that
read/write :class:`~html2md.state.EmitterState`. They must honour the safe-flush
barriers in design §4.7 so streaming never yields output it would later rewrite.

Registration
------------
Each rules module exposes ``HANDLERS: dict[str, TagHandler]`` keyed by lowercase tag
name; ``rules/__init__.py`` merges them into ``TAG_HANDLERS``. To add a tag, add an
entry to the relevant module's ``HANDLERS`` — no emitter change needed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..emitter import MarkdownEmitter


@runtime_checkable
class TagHandler(Protocol):
    """Converts one tag to Markdown via its ``start``/``end`` SAX events."""

    def start(self, em: MarkdownEmitter, attrs: Mapping[str, str]) -> None: ...

    def end(self, em: MarkdownEmitter) -> None: ...


class PrefixSuffixHandler:
    """A **local** rule: wrap the rendered children in a fixed ``prefix``/``suffix``
    (e.g. ``em`` → ``_..._``, ``hr`` → ``"\\n\\n---\\n\\n"`` with empty children). The
    wrap happens at ``end`` so ``em.content`` is the fully rendered children."""

    __slots__ = ("prefix", "suffix")

    def __init__(self, prefix: str = "", suffix: str = "") -> None:
        self.prefix = prefix
        self.suffix = suffix

    def start(self, em: MarkdownEmitter, attrs: Mapping[str, str]) -> None:
        return None

    def end(self, em: MarkdownEmitter) -> None:
        em.emit(self.prefix + em.content + self.suffix)


class TransparentHandler:
    """A structural wrapper (``div``/``section``/``article``/``span``…) that adds no
    Markdown of its own — it passes its rendered children straight through. Registered
    so the element is tracked on the stack (ancestor checks) without altering output."""

    __slots__ = ()

    def start(self, em: MarkdownEmitter, attrs: Mapping[str, str]) -> None:
        return None

    def end(self, em: MarkdownEmitter) -> None:
        em.emit(em.content)
