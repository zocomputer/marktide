"""Block-level rules: p, headings, blockquote, hr, pre/code-block, lists.

Foundation scaffold. The structural-wrapper tags below are registered (they emit no
Markdown, only stack tracking). The block constructs that produce Markdown are filled
in by the block-rules task — most are NON-LOCAL (their output depends on not-yet-seen
events) and must honour the safe-flush barriers in design §4.7:

    p, h1-h6   heading_style underlined (setext, needs text length) / atx / atx_closed
    blockquote "> " prefix applied per produced line
    hr         thematic break
    pre/code   fenced vs indented; backtick run-length; verbatim text (set pre_depth)
    ul/ol/li   nested marker chosen by depth from Options.bullets; list indentation

Add each as a handler and register it in ``HANDLERS``. Reuse
:class:`~html2md.rules.base.PrefixSuffixHandler` for any genuinely local rule.
"""

from __future__ import annotations

from .base import PrefixSuffixHandler, TagHandler, TransparentHandler

# Structural wrappers — tracked on the stack for ancestor checks, pass children through.
_TRANSPARENT = (
    "div", "section", "article", "main", "header", "footer", "nav", "aside",
    "figure", "figcaption", "body", "html",
)

HANDLERS: dict[str, TagHandler] = {tag: TransparentHandler() for tag in _TRANSPARENT}
# Worked example of a local block rule (void element → empty children wrapped).
HANDLERS["hr"] = PrefixSuffixHandler("\n\n---\n\n", "")
