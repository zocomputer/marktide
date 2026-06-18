"""``MarkdownEmitter`` — the lxml target object and Markdown transducer.

It receives SAX callbacks from the incremental parser (``start``/``end``/``data``/
``comment``/``close``), maintains :class:`~html2md.state.EmitterState`, and dispatches
per-tag to the handlers in :data:`~html2md.rules.TAG_HANDLERS`. It is a deterministic
pushdown transducer: output depends only on the event stream and the stack, never on
how bytes were split into feed chunks — that is what guarantees chunk-invariance
(design §4.3, §9).

Buffer model (markdownify's ``convert_X(el, text)`` recursion, done iteratively)
-------------------------------------------------------------------------------
Each open element has its own output buffer (``Frame.content``). Text and child-element
Markdown accumulate into the *current* (innermost open) element's buffer. When an
element ends, its buffer is finalized into a string exposed to the handler as
``em.content`` (the rendered children); the handler emits the element's final Markdown
— typically ``prefix + em.content + suffix``, but it may read/transform the content
(setext underline length, code-fence sizing, empty-element suppression). That emitted
Markdown lands in the *parent's* buffer. At ``close()`` the root buffer is the document.

Division of responsibility (confirmed with the rules tasks)
-----------------------------------------------------------
* The emitter centralises text handling: ``data`` → ``emit_text`` escapes per
  ``Options`` and (later) applies markdownify's boundary whitespace-collapse using the
  parent context on the stack, so every handler stays consistent. Handlers do **not**
  re-escape ``em.content`` — child text is already escaped.
* ``emit`` writes raw Markdown (handler-produced syntax — never escaped).
* ``escape`` is exposed for the rare handler that must escape a string it sources
  itself (e.g. link text built from an ``alt`` attribute).
"""

from __future__ import annotations

from .options import Options
from .rules import TAG_HANDLERS
from .state import EmitterState, Frame

# Characters markdownify escapes when escape_misc is on (foundation subset; the text
# rules refine boundary-sensitive escaping per design §4.7).
_MISC_ESCAPE = str.maketrans({
    "\\": "\\\\", "&": "\\&", "<": "\\<", ">": "\\>",
    "[": "\\[", "]": "\\]", "#": "\\#", "-": "\\-", "+": "\\+",
})


class MarkdownEmitter:
    """SAX target that emits Markdown. ``close()`` returns the assembled document."""

    __slots__ = ("options", "state", "root", "_handlers", "_filter", "_content", "_frame")

    def __init__(self, options: Options | None = None) -> None:
        self.options = options or Options()
        self.state = EmitterState()
        self.root: list[str] = []          # top-level output (document buffer)
        self._handlers = TAG_HANDLERS
        self._filter = _TagFilter(self.options)
        self._content = ""                 # rendered children of element being ended
        self._frame: Frame | None = None   # the element being ended (its own attrs/data)

    # --- handler-facing context API ------------------------------------------

    def _buf(self) -> list[str]:
        """The buffer the current output goes to: the innermost open element's, or the
        document root when nothing is open (or, during ``end``, the parent's)."""
        top = self.state.top
        return top.content if top is not None else self.root

    def emit(self, markdown: str) -> None:
        """Append raw, handler-produced Markdown (never escaped) to the current buffer."""
        if markdown:
            self._buf().append(markdown)

    def emit_text(self, text: str) -> None:
        """Append HTML text content, escaped per options unless inside ``pre``/``code``."""
        if text:
            self._buf().append(text if self.state.in_pre else self.escape(text))

    def escape(self, text: str) -> str:
        """Escape Markdown-significant characters per ``Options``. Verbatim in ``pre``."""
        if self.state.in_pre:
            return text
        if self.options.escape_asterisks:
            text = text.replace("*", "\\*")
        if self.options.escape_underscores:
            text = text.replace("_", "\\_")
        if self.options.escape_misc:
            text = text.translate(_MISC_ESCAPE)
        return text

    @property
    def content(self) -> str:
        """The just-closed element's rendered child Markdown. Valid only inside a
        handler's ``end`` (empty otherwise)."""
        return self._content

    @property
    def frame(self) -> Frame | None:
        """The element being ended — its own ``attrs`` and ``data``. Valid only inside
        a handler's ``end``. This is the just-popped :class:`~html2md.state.Frame`, so a
        handler reads *its own* per-element attributes/bookkeeping even when the same
        tag is nested (``<a><a></a></a>``); ``em.state.top`` at ``end`` is the parent."""
        return self._frame

    # --- lxml target protocol (SAX callbacks) --------------------------------

    def start(self, tag: str, attrs: dict[str, str]) -> None:
        tag = tag.lower()
        frame = self.state.push(tag, dict(attrs))
        handler = self._handlers.get(tag)
        # start mutates state / captures attrs (e.g. pre_depth, list context, href);
        # output is produced at end from the rendered children.
        if handler is not None and self._filter.converts(tag):
            handler.start(self, frame.attrs)

    def end(self, tag: str) -> None:
        tag = tag.lower()
        frame = self.state.pop()
        if frame is None:
            return
        content = "".join(frame.content)
        handler = self._handlers.get(tag)
        if handler is not None and self._filter.converts(tag):
            self._content = content
            self._frame = frame            # the just-popped element (its own attrs/data)
            try:
                handler.end(self)          # emits into the parent buffer
            finally:
                self._content = ""
                self._frame = None
        else:
            # no handler / filtered-out: children pass through unchanged
            self.emit(content)

    def data(self, data: str) -> None:
        self.emit_text(data)

    def comment(self, text: str) -> None:
        return None  # markdownify drops HTML comments

    def close(self) -> str:
        return _apply_document_strip("".join(self.root), self.options.strip_document)


class _TagFilter:
    """markdownify ``strip``/``convert`` tag-filter semantics. ``convert`` is an
    allowlist (only these convert); ``strip`` is a denylist (these emit children only).
    Mutually exclusive (enforced in :class:`Options`)."""

    __slots__ = ("_convert", "_strip")

    def __init__(self, options: Options) -> None:
        self._convert = set(options.convert) if options.convert is not None else None
        self._strip = set(options.strip) if options.strip is not None else None

    def converts(self, tag: str) -> bool:
        if self._convert is not None:
            return tag in self._convert
        if self._strip is not None:
            return tag not in self._strip
        return True


def _apply_document_strip(text: str, mode: str | None) -> str:
    if mode == "strip":
        return text.strip()
    if mode == "lstrip":
        return text.lstrip()
    if mode == "rstrip":
        return text.rstrip()
    return text
