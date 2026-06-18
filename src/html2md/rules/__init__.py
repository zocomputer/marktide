"""Tag-handler dispatch table.

``TAG_HANDLERS`` maps a lowercase tag name to its :class:`~html2md.rules.base.TagHandler`.
It is assembled by merging each rule module's ``HANDLERS`` dict, so a new tag is added
by editing the relevant module — never the emitter. A tag with no entry falls through:
its element is still tracked on the state stack and its text content is emitted, but it
contributes no Markdown of its own.
"""

from __future__ import annotations

from . import blocks, inline, tables
from .base import PrefixSuffixHandler, TagHandler, TransparentHandler

TAG_HANDLERS: dict[str, TagHandler] = {}
for _module in (blocks, inline, tables):
    TAG_HANDLERS.update(_module.HANDLERS)

__all__ = ["TAG_HANDLERS", "TagHandler", "PrefixSuffixHandler", "TransparentHandler"]
