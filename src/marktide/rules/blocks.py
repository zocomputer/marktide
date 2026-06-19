"""Block-level rules: paragraphs, headings, blockquote, hr, pre, lists.

Each handler reproduces the corresponding ``markdownify==1.2.2`` ``convert_*`` function,
operating on the element's rendered children (``em.content``) at ``end``. Block handlers
emit their own surrounding ``\\n\\n`` separators exactly as markdownify does; the emitter
collapses adjacent separators at child boundaries (markdownify's ``process_tag`` newline
collapse) and ``strip_document`` trims the ends.

List handlers are state-driven (``EmitterState.list_stack``), not tree-driven: the bullet
char and ordered index come from the :class:`~marktide.state.ListContext` pushed at the
``ul``/``ol`` ``start``, so no parent/sibling navigation is needed.
"""

from __future__ import annotations

import re
from textwrap import fill

from ..state import ListContext
from .base import PrefixSuffixHandler, TagHandler, TransparentHandler

# markdownify regexes (verbatim) used by the block converters.
_RE_LINE = re.compile(r"^(.*)", flags=re.MULTILINE)
_RE_ALL_WS = re.compile(r"[\t \r\n]+")
_RE_PRE_LSTRIP = re.compile(r"^[ \n]*\n")
_RE_PRE_RSTRIP = re.compile(r"[ \n]*$")
_RE_PRE_LSTRIP1 = re.compile(r"^ *\n")
_RE_PRE_RSTRIP1 = re.compile(r"\n *$")

_HEADING_TAGS = frozenset(f"h{n}" for n in range(1, 7))
_CELL_TAGS = frozenset(("td", "th"))
_NOFORMAT_TAGS = frozenset(("pre", "code", "kbd", "samp"))


# --- shared SAX-context helpers (markdownify parent_tags equivalents) -----------
# At end() the element's own frame is already popped, so em.state.stack holds the
# element's ancestors — exactly markdownify's parent_tags for the convert_* call.

def in_inline(em) -> bool:
    """markdownify's ``_inline`` pseudo-tag: an ancestor heading or table cell."""
    return any(f.tag in _HEADING_TAGS or f.tag in _CELL_TAGS for f in em.state.stack)


def in_noformat(em) -> bool:
    """markdownify's ``_noformat`` pseudo-tag: an ancestor pre/code/kbd/samp."""
    return any(f.tag in _NOFORMAT_TAGS for f in em.state.stack)


def chomp(text: str) -> tuple[str, str, str]:
    """markdownify ``chomp``: pull a leading/trailing space out as prefix/suffix."""
    prefix = " " if text and text[0] == " " else ""
    suffix = " " if text and text[-1] == " " else ""
    return prefix, suffix, text.strip()


def _underline(text: str, pad_char: str) -> str:
    text = (text or "").rstrip()
    return "\n\n%s\n%s\n\n" % (text, pad_char * len(text)) if text else ""


def _strip_pre(text: str) -> str:
    text = _RE_PRE_LSTRIP.sub("", text)
    text = _RE_PRE_RSTRIP.sub("", text)
    return text


def _strip1_pre(text: str) -> str:
    """Strip a single leading and trailing newline (markdownify ``strip_one``)."""
    text = _RE_PRE_LSTRIP1.sub("", text)
    text = _RE_PRE_RSTRIP1.sub("", text)
    return text


# --- handlers ------------------------------------------------------------------

class _Paragraph:
    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        if in_inline(em):
            em.emit(" " + em.content.strip(" \t\r\n") + " ")
            return
        text = em.content.strip(" \t\r\n")
        if em.options.wrap and em.options.wrap_width is not None:
            new_lines = []
            for line in text.split("\n"):
                line = line.lstrip(" \t\r\n")
                trailing = line[len(line.rstrip()):]
                line = fill(
                    line,
                    width=em.options.wrap_width,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                new_lines.append(line + trailing)
            text = "\n".join(new_lines)
        em.emit("\n\n%s\n\n" % text if text else "")


class _Heading:
    __slots__ = ("n",)

    def __init__(self, n: int) -> None:
        self.n = n

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        if in_inline(em):
            em.emit(em.content)
            return
        n = max(1, min(6, self.n))
        text = em.content.strip()
        style = em.options.heading_style
        if style == "underlined" and n <= 2:
            em.emit(_underline(text, "=" if n == 1 else "-"))
            return
        text = _RE_ALL_WS.sub(" ", text)
        hashes = "#" * n
        if style == "atx_closed":
            em.emit("\n\n%s %s %s\n\n" % (hashes, text, hashes))
        else:
            em.emit("\n\n%s %s\n\n" % (hashes, text))


class _Blockquote:
    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        text = (em.content or "").strip(" \t\r\n")
        if in_inline(em):
            em.emit(" " + text + " ")
            return
        if not text:
            em.emit("\n")
            return

        def _indent(match):
            line = match.group(1)
            return "> " + line if line else ">"

        em.emit("\n" + _RE_LINE.sub(_indent, text) + "\n\n")


class _Pre:
    __slots__ = ()

    def start(self, em, attrs) -> None:
        em.state.pre_depth += 1

    def end(self, em) -> None:
        em.state.pre_depth -= 1
        text = em.content
        if not text:
            em.emit("")
            return
        code_language = em.options.code_language
        if em.options.code_language_callback is not None:
            # markdownify passes the element; marktide hands the just-popped frame.
            code_language = em.options.code_language_callback(em.frame) or code_language
        if em.options.strip_pre == "strip":
            text = _strip_pre(text)
        elif em.options.strip_pre == "strip_one":
            text = _strip1_pre(text)
        em.emit("\n\n```%s\n%s\n```\n\n" % (code_language, text))


class _ListContainer:
    """``ul``/``ol`` — pushes a :class:`ListContext` at start, emits the wrapped items
    at end. Nested lists (an ``li`` ancestor) drop the leading blank line."""

    __slots__ = ("ordered",)

    def __init__(self, ordered: bool) -> None:
        self.ordered = ordered

    def start(self, em, attrs) -> None:
        if self.ordered:
            raw = attrs.get("start")
            index = int(raw) if raw is not None and str(raw).isnumeric() else 1
            marker = ""
        else:
            depth = sum(1 for ctx in em.state.list_stack if not ctx.ordered)
            bullets = em.options.bullets
            marker = bullets[depth % len(bullets)]
            index = 0
        em.state.list_stack.append(ListContext(self.ordered, index, marker))

    def end(self, em) -> None:
        if em.state.list_stack:
            em.state.list_stack.pop()
        text = em.content
        # Nested list (inside an <li>): no leading blank line, trim trailing.
        if em.state.has_ancestor("li"):
            em.emit("\n" + text.rstrip())
        elif not text.strip():
            # Empty list: markdownify's convert_list emits '\n\n' + ('\n' if
            # before_paragraph else ''). before_paragraph is a forward-looking
            # next-sibling check (true unless the next block-content sibling is another
            # list), so defer the whole output to the next SAX event — chunk-invariant,
            # mirroring the pending_ws deferral. A non-empty list (below) anchors its
            # content so the fixed trailing '\n\n' collapses correctly without lookahead,
            # but an all-newline empty list cannot, which is why only this branch defers.
            em.mark_empty_list_pending()
        else:
            # Non-empty list: emit the trailing '\n\n' unconditionally; the emitter's
            # trailing-newline hold-back drops it at document end and boundary-collapse
            # caps it at one blank line before a following list/block. (Verified against
            # markdownify across the list-boundary cases.)
            em.emit("\n\n" + text.rstrip() + "\n\n")


class _ListItem:
    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        text = (em.content or "").strip()
        if not text:
            em.emit("\n")
            return
        ctx = em.state.list_stack[-1] if em.state.list_stack else None
        if ctx is not None and ctx.ordered:
            bullet = "%s." % ctx.index
            ctx.index += 1
        elif ctx is not None:
            bullet = ctx.marker
        else:
            bullet = "*"
        bullet += " "
        width = len(bullet)
        indent = " " * width

        def _indent(match):
            line = match.group(1)
            return indent + line if line else ""

        text = _RE_LINE.sub(_indent, text)
        text = bullet + text[width:]
        em.emit("%s\n" % text)


class _Div:
    """``div``/``section``/``article``/``dl`` (markdownify ``convert_div``) — a block that
    wraps its stripped children in surrounding blank lines, or ``' text '`` inline."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        if in_inline(em):
            em.emit(" " + em.content.strip() + " ")
            return
        text = em.content.strip()
        em.emit("\n\n%s\n\n" % text if text else "")


class _DefTerm:
    """``dt`` — definition term. One line, whitespace flattened (markdownify ``convert_dt``)."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        text = _RE_ALL_WS.sub(" ", (em.content or "").strip())
        if in_inline(em):
            em.emit(" " + text + " ")
            return
        em.emit("\n\n%s\n" % text if text else "\n")


class _DefDesc:
    """``dd`` — definition description: indent 4 spaces, lead with ``:`` (markdownify
    ``convert_dd``)."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        text = (em.content or "").strip()
        if in_inline(em):
            em.emit(" " + text + " ")
            return
        if not text:
            em.emit("\n")
            return

        def _indent(match):
            line = match.group(1)
            return "    " + line if line else ""

        text = _RE_LINE.sub(_indent, text)
        text = ":" + text[1:]
        em.emit("%s\n" % text)


class _Figcaption:
    """``figcaption`` (markdownify ``convert_figcaption``) — block, stripped, blank-line wrapped."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        em.emit("\n\n" + em.content.strip() + "\n\n")


class _Drop:
    """``script``/``style`` — dropped entirely (markdownify ``convert_script``/``convert_style``
    return ``''``). The children rendered into the frame buffer are discarded."""

    __slots__ = ()

    def start(self, em, attrs) -> None:
        return None

    def end(self, em) -> None:
        return None


# Structural wrappers with NO markdownify converter — tracked on the stack for ancestor
# checks, pass children through. (div/section/article/dl are NOT here: markdownify's
# convert_div makes them blocks — see _Div.)
_TRANSPARENT = (
    "main", "header", "footer", "nav", "aside", "figure", "body", "html",
)

_DIV = _Div()
_DROP = _Drop()

HANDLERS: dict[str, TagHandler] = {tag: TransparentHandler() for tag in _TRANSPARENT}
HANDLERS["p"] = _Paragraph()
for _n in range(1, 7):
    HANDLERS["h%d" % _n] = _Heading(_n)
HANDLERS["blockquote"] = _Blockquote()
HANDLERS["hr"] = PrefixSuffixHandler("\n\n---\n\n", "")
HANDLERS["pre"] = _Pre()
HANDLERS["ul"] = _ListContainer(ordered=False)
HANDLERS["ol"] = _ListContainer(ordered=True)
HANDLERS["li"] = _ListItem()
HANDLERS["div"] = _DIV
HANDLERS["section"] = _DIV
HANDLERS["article"] = _DIV
HANDLERS["dl"] = _DIV
HANDLERS["dt"] = _DefTerm()
HANDLERS["dd"] = _DefDesc()
HANDLERS["figcaption"] = _Figcaption()
HANDLERS["script"] = _DROP
HANDLERS["style"] = _DROP
