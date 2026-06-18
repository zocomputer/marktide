"""Inline rules: links, images, emphasis, code, line breaks, sub/sup, spans.

Foundation scaffold. One worked local example (``strong``) shows the contract; the
rest are filled in by the inline-rules task. Links and images are NON-LOCAL (the href/
title/alt are only fully known at ``end``/from attrs) and must honour the safe-flush
barriers in design §4.7 — capture what you need onto ``em.state.top.data`` at ``start``
and emit at ``end``:

    a          [text](href "title"); autolinks; options.autolinks / default_title
    img        ![alt](src "title"); keep_inline_images_in
    strong/b   options.strong_em_symbol doubled
    em/i       options.strong_em_symbol
    code       inline backticks with run-length escaping; verbatim text
    br         newline_style: two trailing spaces (spaces) or backslash
    sub/sup    options.sub_symbol / sup_symbol
    span       transparent

Register each in ``HANDLERS``. Use :class:`~html2md.rules.base.PrefixSuffixHandler`
for local rules.
"""

from __future__ import annotations

from .base import PrefixSuffixHandler, TagHandler, TransparentHandler

# Worked example of a local inline rule (option-aware variants are the rules task's
# job; this demonstrates the PrefixSuffixHandler contract for the foundation).
_STRONG = PrefixSuffixHandler("**", "**")

HANDLERS: dict[str, TagHandler] = {
    "span": TransparentHandler(),
    "strong": _STRONG,
    "b": _STRONG,
}
