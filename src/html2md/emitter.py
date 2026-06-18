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

import re

from .options import Options
from .rules import TAG_HANDLERS
from .state import EmitterState, Frame

# markdownify==1.2.2 regexes (verbatim) for whitespace normalisation, child-boundary
# newline collapse, and escape_misc — reproduced so output matches the oracle exactly.
_RE_WHITESPACE = re.compile(r"[\t ]+")
_RE_ALL_WHITESPACE = re.compile(r"[\t \r\n]+")
_RE_NEWLINE_WHITESPACE = re.compile(r"[\t \r\n]*[\r\n][\t \r\n]*")
_RE_EXTRACT_NEWLINES = re.compile(r"^(\n*)((?:.*[^\n])?)(\n*)$", flags=re.DOTALL)
_RE_ESCAPE_MISC_CHARS = re.compile(r"([]\\&<`[>~=+|])")
_RE_ESCAPE_MISC_DASH = re.compile(r"(\s|^)(-+(?:\s|$))")
_RE_ESCAPE_MISC_HASHES = re.compile(r"(\s|^)(#{1,6}(?:\s|$))")
_RE_ESCAPE_MISC_LIST = re.compile(r"((?:\s|^)[0-9]{1,9})([.)](?:\s|$))")

# markdownify's `_noformat` pseudo-tag: inside any of these, text is not escaped.
_NOFORMAT_TAGS = frozenset(("pre", "code", "kbd", "samp"))

# markdownify should_remove_whitespace_inside: whitespace immediately inside these
# block-level elements is trimmed at their edges. should_remove_whitespace_outside is
# this set plus `pre` — used to drop whitespace adjacent to a block sibling (item-D).
_BLOCK_INSIDE_TAGS = frozenset((
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "blockquote", "article", "div", "section",
    "ol", "ul", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tfoot", "tr", "td", "th",
))


def _is_block_outside(tag: str) -> bool:
    """markdownify should_remove_whitespace_outside: a block element or pre."""
    return tag in _BLOCK_INSIDE_TAGS or tag == "pre"


class MarkdownEmitter:
    """SAX target that emits Markdown. ``close()`` returns the assembled document."""

    __slots__ = (
        "options", "state", "root", "_handlers", "_filter", "_content", "_frame",
        "_started", "_carry", "_tail", "_text_buf",
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
        self._carry = ""                   # collapse-fold carry: last root child's
        #                                    trailing newlines (markdownify merge quirk)
        self._tail = ""                    # trailing newlines of emitted output, held
        #                                    back for the document rstrip (O(1))
        self._text_buf: list[str] = []     # consecutive data() coalesced into one text
        #                                    node (lxml splits special-element text by
        #                                    feed boundary; coalescing makes it
        #                                    chunk-invariant before normalisation)

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
        """Append HTML text content, reproducing markdownify's ``process_text``:
        normalise whitespace unless inside ``pre``, escape unless inside a ``_noformat``
        element (``pre``/``code``/``kbd``/``samp``), then trim whitespace adjacent to
        block siblings (item-D). The trailing whitespace is *deferred* one event (held on
        the parent frame) so the next sibling can decide whether to drop it — a bounded
        O(1) lookahead that preserves streaming and chunk-invariance."""
        if not text:
            return
        in_pre = self.state.pre_depth > 0
        if not in_pre:
            if self.options.wrap:
                text = _RE_ALL_WHITESPACE.sub(" ", text)
            else:
                text = _RE_NEWLINE_WHITESPACE.sub("\n", text)
                text = _RE_WHITESPACE.sub(" ", text)
        if not self._in_noformat():
            text = self.escape(text)
        if not text:
            return
        buf = self._buf()
        parent = self.state.top
        if parent is None:
            buf.append(text)  # top-level text with no element wrapper (lxml normally wraps)
            return
        # A previous text sibling's deferred trailing whitespace is kept (this neighbour
        # is more text, not a block).
        if parent.pending_ws:
            buf.append(parent.pending_ws)
            parent.pending_ws = ""
        # D leading trim: drop leading whitespace after a block sibling, or as the first
        # child of a block-level element.
        if not in_pre and (
            parent.last_child_block
            or (not parent.seen_child and parent.tag in _BLOCK_INSIDE_TAGS)
        ):
            text = text.lstrip(" \t\r\n")
        if in_pre:
            body, trailing = text, ""
        else:
            body = text.rstrip(" \t\r\n")
            trailing = text[len(body):]
        if body:
            buf.append(body)
        parent.pending_ws = trailing  # defer: dropped if the next sibling is a block
        parent.seen_child = True
        parent.last_child_block = False

    def escape(self, text: str) -> str:
        """Escape Markdown-significant characters per ``Options`` (markdownify ``escape``).
        Does not consult element context — the ``_noformat`` skip lives in ``emit_text``;
        handlers may call this for a string they source themselves."""
        if not text:
            return ""
        if self.options.escape_misc:
            text = _RE_ESCAPE_MISC_CHARS.sub(r"\\\1", text)
            text = _RE_ESCAPE_MISC_DASH.sub(r"\1\\\2", text)
            text = _RE_ESCAPE_MISC_HASHES.sub(r"\1\\\2", text)
            text = _RE_ESCAPE_MISC_LIST.sub(r"\1\\\2", text)
        if self.options.escape_asterisks:
            text = text.replace("*", r"\*")
        if self.options.escape_underscores:
            text = text.replace("_", r"\_")
        return text

    def _in_noformat(self) -> bool:
        """True if any open ancestor is pre/code/kbd/samp (markdownify ``_noformat``)."""
        return any(frame.tag in _NOFORMAT_TAGS for frame in self.state.stack)

    @staticmethod
    def _collapse_join(parts: list[str], prefix: str = "") -> str:
        """Join child-output strings, collapsing newlines at each boundary to at most
        two (markdownify ``process_tag``). ``prefix`` seeds the look-back with output
        already committed before this batch (used to collapse across drains)."""
        updated = [""]
        if prefix:
            updated.append(prefix)
        for child in parts:
            if not child:
                continue
            leading, content, trailing = _RE_EXTRACT_NEWLINES.match(child).groups()
            if updated[-1] and leading:
                prev = updated.pop()
                leading = "\n" * min(2, max(len(prev), len(leading)))
            updated.append(leading)
            updated.append(content)
            updated.append(trailing)
        return "".join(updated)

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
        self._flush_text()  # finalise the preceding text node before this child
        tag = tag.lower()
        # Resolve the parent's deferred text whitespace now that the next sibling (this
        # element) is known: drop it before a block, keep it before an inline element.
        parent = self.state.top
        if parent is not None:
            if parent.pending_ws:
                if not _is_block_outside(tag):
                    self._buf().append(parent.pending_ws)
                parent.pending_ws = ""
            parent.seen_child = True
            parent.last_child_block = _is_block_outside(tag)
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
        self._flush_text()  # finalise this element's trailing text before it closes
        tag = tag.lower()
        frame = self.state.pop()
        if frame is None:
            return
        # This element's last text child has no next sibling: keep its deferred trailing
        # whitespace only if the element is not block-level (markdownify rstrips the last
        # text inside a block element).
        if frame.pending_ws:
            if frame.tag not in _BLOCK_INSIDE_TAGS:
                frame.content.append(frame.pending_ws)
            frame.pending_ws = ""
        # Join children, collapsing newlines at boundaries — except inside pre, where
        # newlines are verbatim. pre_depth still counts this element here (the pre
        # handler decrements it in its own end, which runs below).
        if self.state.pre_depth > 0:
            content = "".join(frame.content)
        else:
            content = self._collapse_join(frame.content)
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
        # Coalesce: lxml may split one text node across several data() callbacks at feed
        # boundaries. Buffer and process the whole run on the next non-data event so
        # whitespace normalisation sees the complete text node (chunk-invariance).
        if data:
            self._text_buf.append(data)

    def _flush_text(self) -> None:
        if self._text_buf:
            text = "".join(self._text_buf)
            self._text_buf.clear()
            self.emit_text(text)

    def comment(self, text: str) -> None:
        self._flush_text()
        # lxml surfaces an HTML CDATA section as a comment "[CDATA[...]]"; markdownify
        # emits the CDATA content as text. Ordinary comments are dropped.
        if text.startswith("[CDATA[") and text.endswith("]]"):
            self.emit_text(text[7:-2])

    # --- streaming drain / final flush ---------------------------------------

    def drain(self) -> str:
        """Return the Markdown that is safe to yield NOW (streaming), removing it from
        the buffer. The safe-emission barrier (design §4.7): trailing whitespace is held
        back — it may be ``rstrip``-ped at ``close`` or merged at a following sibling
        boundary — and the leading ``strip_document`` is applied once, so a drained
        prefix is never rewritten by later events. Top-level output only reaches the
        buffer when an element fully closes, so what is drained is already complete."""
        s = self._tail + self._fold_children(self.root)
        self.root.clear()
        if not self._started and self.options.strip_document in ("strip", "lstrip"):
            s = s.lstrip("\n")
        if s and not self._started:
            self._started = True
        # Hold back trailing newlines: they may be document-trailing (rstripped at
        # close) — emitting them now would leak a trailing separator a later close can
        # no longer remove. Re-prepended to the next drain when more content follows.
        body = s.rstrip("\n")
        self._tail = s[len(body):]
        return body

    def close(self) -> str:
        """Flush all buffered output with the document-level strip applied (markdownify
        ``convert__document_`` strips separator newlines only). Works whether or not
        ``drain`` was called first (one-shot ``convert`` vs streaming)."""
        self._flush_text()  # finalise any trailing text node
        s = self._tail + self._fold_children(self.root) + self._carry  # flush all held
        self.root.clear()
        self._carry = ""
        self._tail = ""
        mode = self.options.strip_document
        if not self._started and mode in ("strip", "lstrip"):
            s = s.lstrip("\n")
        if mode in ("strip", "rstrip"):
            s = s.rstrip("\n")
        self._started = True
        return s

    def _fold_children(self, children: list[str]) -> str:
        """Resumable child-boundary newline collapse over the streamed root children
        (markdownify ``process_tag``), carrying the unstable trailing-newline state in
        ``self._carry`` so the result is identical no matter where drains split the
        stream — the chunk-invariance guarantee (§9.1). Returns the now-stable output;
        the new carry (the last child's trailing newlines, which a future child could
        still collapse against) is withheld until ``close`` or the next child."""
        out: list[str] = []
        carry = self._carry
        for child in children:
            if not child:
                continue
            leading, content, trailing = _RE_EXTRACT_NEWLINES.match(child).groups()
            if carry and leading:
                # previous child's trailing newlines collapse with this leading (≤2)
                out.append("\n" * min(2, max(len(carry), len(leading))))
            else:
                # carry did not collapse (e.g. a pure-newline child broke the run) —
                # emit it verbatim, then this leading, exactly as the whole-doc fold does
                out.append(carry)
                out.append(leading)
            out.append(content)
            carry = trailing
        self._carry = carry
        return "".join(out)


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
