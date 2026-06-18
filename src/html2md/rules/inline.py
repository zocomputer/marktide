"""Inline rules: emphasis, code spans, line breaks, spans.

Each handler reproduces the ``markdownify==1.2.2`` ``convert_*`` function on the element's
rendered children (``em.content``). Links (``a``) and images (``img``) are attribute-driven
and land once the foundation exposes element attributes at ``end``; they are intentionally
absent here for now.

``em.content`` is already escaped by the emitter's text path, so handlers never re-escape;
inside a ``_noformat`` ancestor (pre/code/kbd/samp) markdownify passes inline markup straight
through, which :func:`~html2md.rules.blocks.in_noformat` detects.
"""

from __future__ import annotations

import re

from .base import TagHandler, TransparentHandler
from .blocks import chomp, in_inline, in_noformat

_RE_BACKTICKS = re.compile(r"`+")


def _markup_pair(markup: str) -> tuple[str, str]:
    """markdownify ``abstract_inline_conversion``: an HTML-tag-shaped markup like ``<sub>``
    closes with ``</sub>``; everything else (``**``, ``*``, ``~~``) is symmetric."""
    if markup.startswith("<") and markup.endswith(">"):
        return markup, "</" + markup[1:]
    return markup, markup


def _emit_inline(em, markup: str) -> None:
    """markdownify ``abstract_inline_conversion`` body: pass through inside ``_noformat``,
    else wrap the chomped children, suppressing empty content."""
    content = em.content
    if in_noformat(em):
        em.emit(content)
        return
    prefix, suffix, text = chomp(content)
    if not text:
        return
    open_markup, close_markup = _markup_pair(markup)
    em.emit("%s%s%s%s%s" % (prefix, open_markup, text, close_markup, suffix))


class _Strong:
    """``strong``/``b`` → ``strong_em_symbol`` doubled (option-aware)."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        _emit_inline(em, em.options.strong_em_symbol * 2)


class _Emphasis:
    """``em``/``i`` → ``strong_em_symbol`` (option-aware)."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        _emit_inline(em, em.options.strong_em_symbol)


class _Del:
    """``del``/``s``/``strike`` → ``~~`` strikethrough."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        _emit_inline(em, "~~")


class _Sub:
    """``sub`` → ``options.sub_symbol`` (empty by default → plain text)."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        _emit_inline(em, em.options.sub_symbol)


class _Sup:
    """``sup`` → ``options.sup_symbol`` (empty by default → plain text)."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        _emit_inline(em, em.options.sup_symbol)


def _markdownify_code_span(text: str) -> tuple[str, str]:
    """Return markdownify-compatible inline-code delimiter and text."""
    max_backticks = max((len(m.group()) for m in _RE_BACKTICKS.finditer(text)), default=0)
    delimiter = "`" * (max_backticks + 1)
    if max_backticks > 0:
        text = " " + text + " "
    return delimiter, text


def _commonmark_stable_code_span(text: str) -> tuple[str, str]:
    """Return a CommonMark-valid, text-idempotent inline-code delimiter and text.

    CommonMark permits any delimiter length that is not present as a maximal backtick
    run in the code text. Choosing the smallest absent length gives a canonical form
    that survives a render-to-HTML-and-convert-back pass for adjacent code spans such
    as ``<code>0</code><code>0</code>``. Padding is only needed when the code text
    starts or ends with a backtick; otherwise an edge backtick would merge with the
    delimiter and stop it being parsed as the intended opening/closing run.
    """
    run_lengths = {len(m.group()) for m in _RE_BACKTICKS.finditer(text)}
    delimiter_length = 1
    while delimiter_length in run_lengths:
        delimiter_length += 1
    delimiter = "`" * delimiter_length
    if text.startswith("`") or text.endswith("`"):
        text = " " + text + " "
    return delimiter, text


class _Code:
    """``code``/``kbd``/``samp`` inline span.

    Defaults to markdownify-compatible delimiter selection: one more backtick than the
    longest backtick run in the content, padding when the content contains any
    backtick. With ``Options.commonmark_roundtrip_stable=True``, uses a canonical
    CommonMark delimiter policy instead. Passes through unchanged inside a
    ``_noformat`` ancestor.
    """

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        content = em.content
        if in_noformat(em):
            em.emit(content)
            return
        prefix, suffix, text = chomp(content)
        if not text:
            return
        if em.options.commonmark_roundtrip_stable:
            delimiter, text = _commonmark_stable_code_span(text)
        else:
            delimiter, text = _markdownify_code_span(text)
        em.emit("%s%s%s%s%s" % (prefix, delimiter, text, delimiter, suffix))


class _Break:
    """``br`` → two trailing spaces + newline (``spaces``) or ``\\`` + newline
    (``backslash``); a single space inside an ``_inline`` ancestor."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        if in_inline(em):
            em.emit(" ")
            return
        if em.options.newline_style == "backslash":
            em.emit("\\\n")
        else:
            em.emit("  \n")


class _Link:
    """``a`` → ``[text](href "title")``, with markdownify's autolink shortcut when the
    link text equals the href. Reads ``href``/``title`` from the just-popped frame at
    ``end``. Passes children through inside a ``_noformat`` ancestor."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        content = em.content
        if in_noformat(em):
            em.emit(content)
            return
        prefix, suffix, text = chomp(content)
        if not text:
            return
        attrs = em.frame.attrs if em.frame is not None else {}
        href = attrs.get("href")
        title = attrs.get("title")
        if (em.options.autolinks
                and text.replace(r"\_", "_") == href
                and not title
                and not em.options.default_title):
            em.emit("<%s>" % href)
            return
        if em.options.default_title and not title:
            title = href
        title_part = ' "%s"' % title.replace('"', r"\"") if title else ""
        if href:
            em.emit("%s[%s](%s%s)%s" % (prefix, text, href, title_part, suffix))
        else:
            em.emit(text)


class _Image:
    """``img`` → ``![alt](src "title")``. Void element (no children); ``alt``/``src``/
    ``title`` are read from the frame and used verbatim (markdownify does not escape them).
    Inside an ``_inline`` ancestor it degrades to the alt text unless the parent is in
    ``keep_inline_images_in``."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        attrs = em.frame.attrs if em.frame is not None else {}
        alt = attrs.get("alt") or ""
        src = attrs.get("src") or ""
        title = attrs.get("title") or ""
        title_part = ' "%s"' % title.replace('"', r"\"") if title else ""
        if in_inline(em):
            parent = em.state.top
            if parent is None or parent.tag not in em.options.keep_inline_images_in:
                em.emit(alt)
                return
        em.emit("![%s](%s%s)" % (alt, src, title_part))


class _Quote:
    """``q`` (markdownify ``convert_q``) — wrap children in straight double quotes."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        em.emit('"' + em.content + '"')


class _Source:
    """``source`` — captures the first ``src`` onto the parent media frame so the
    enclosing :class:`_Video` can use it when the media element has no own ``src``."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        stack = em.state.stack
        parent = stack[-2] if len(stack) >= 2 else None
        if parent is not None and parent.tag in ("video", "audio", "picture"):
            src = attrs.get("src")
            if src and "media_source_src" not in parent.data:
                parent.data["media_source_src"] = src

    def end(self, em) -> None:
        return None


class _Video:
    """``video`` (markdownify ``convert_video``) — link/poster image depending on which of
    ``src`` (own or first ``<source>``) and ``poster`` are present; degrades to caption text
    inside an ``_inline`` ancestor unless the parent is in ``keep_inline_images_in``."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        text = em.content
        frame = em.frame
        attrs = frame.attrs if frame is not None else {}
        if in_inline(em):
            parent = em.state.top
            if parent is None or parent.tag not in em.options.keep_inline_images_in:
                em.emit(text)
                return
        src = attrs.get("src") or ""
        if not src and frame is not None:
            src = frame.data.get("media_source_src") or ""
        poster = attrs.get("poster") or ""
        if src and poster:
            em.emit("[![%s](%s)](%s)" % (text, poster, src))
        elif src:
            em.emit("[%s](%s)" % (text, src))
        elif poster:
            em.emit("![%s](%s)" % (text, poster))
        else:
            em.emit(text)


HANDLERS: dict[str, TagHandler] = {
    "span": TransparentHandler(),
    "q": _Quote(),
    "video": _Video(),
    "source": _Source(),
    "strong": _Strong(),
    "b": _Strong(),
    "em": _Emphasis(),
    "i": _Emphasis(),
    "code": _Code(),
    "kbd": _Code(),
    "samp": _Code(),
    "br": _Break(),
    "a": _Link(),
    "img": _Image(),
    "del": _Del(),
    "s": _Del(),
    "strike": _Del(),
    "sub": _Sub(),
    "sup": _Sup(),
}
