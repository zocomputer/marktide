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

    __slots__ = (
        "options", "state", "root", "_handlers", "_filter", "_content", "_frame",
        "_started", "_pending_tail",
    )

    def __init__(self, options: Options | None = None) -> None:
        self.options = options or Options()
        self.state = EmitterState()
        self.root: list[str] = []          # top-level output committed since last drain
        self._handlers = TAG_HANDLERS
        self._filter = _TagFilter(self.options)
        self._content = ""                 # rendered children of element being ended
        self._frame: Frame | None = None   # the element being ended (its own attrs/data)
        self._started = False              # have we emitted leading (post-lstrip) output?
        self._pending_tail = ""            # trailing whitespace held back across drains

    # --- handler-facing context API ------------------------------------------

    def _buf(self) -> list[str]:
        """The buffer current output goes to: the nearest enclosing *buffering* element's
        content, or the drainable document root if every open ancestor is a transparent
        streaming container. This is what lets completed top-level blocks reach the root
        (and stream out) while the always-open <html>/<body> wrappers don't trap them."""
        for frame in reversed(self.state.stack):
            if frame.buffering:
                return frame.content
        return self.root

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
        converts = handler is not None and self._filter.converts(tag)
        # A transparent/streaming handler (or an unhandled/filtered tag, which passes its
        # children through) does not buffer — its children stream to the nearest buffering
        # ancestor. Everything else wraps its children and buffers until end.
        frame.buffering = converts and not getattr(handler, "streaming", False)
        if converts:
            # start mutates state / captures attrs (e.g. pre_depth, list context, href);
            # output is produced at end from the rendered children.
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

    # --- streaming drain / final flush ---------------------------------------

    def drain(self) -> str:
        """Return the Markdown that is safe to yield NOW (streaming), removing it from
        the buffer. The safe-emission barrier (design §4.7): trailing whitespace is held
        back — it may be ``rstrip``-ped at ``close`` or merged at a following sibling
        boundary — and the leading ``strip_document`` is applied once, so a drained
        prefix is never rewritten by later events. Top-level output only reaches the
        buffer when an element fully closes, so what is drained is already complete."""
        s = self._pending_tail + "".join(self.root)
        self.root.clear()
        self._pending_tail = ""
        if not self._started and self.options.strip_document in ("strip", "lstrip"):
            s = s.lstrip()
        if s and not self._started:
            self._started = True
        body = s.rstrip()
        self._pending_tail = s[len(body):]  # held-back trailing whitespace (only)
        return body

    def close(self) -> str:
        """Flush all buffered output with the document-level strip applied. Works
        whether or not ``drain`` was called first (one-shot ``convert`` vs streaming)."""
        s = self._pending_tail + "".join(self.root)
        self.root.clear()
        self._pending_tail = ""
        mode = self.options.strip_document
        if not self._started and mode in ("strip", "lstrip"):
            s = s.lstrip()
        if mode in ("strip", "rstrip"):
            s = s.rstrip()
        self._started = True
        return s


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
