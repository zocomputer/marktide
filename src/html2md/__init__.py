"""html2md — fast streaming HTML → Markdown conversion built on lxml.

Public API::

    from html2md import convert, convert_async, convert_stream, convert_stream_async
    from html2md import Options, markdownify_compat

    md = convert("<h1>Hi</h1>")                       # one-shot, sync
    md = await convert_async(html_bytes)              # one-shot, off the event loop
    for chunk in convert_stream(byte_chunks): ...     # streaming, sync
    async for chunk in convert_stream_async(achunks): # streaming, async
        ...

Options default to ``markdownify==1.2.2`` behavior; ``markdownify_compat(**kwargs)``
maps markdownify keyword arguments onto :class:`Options` for drop-in migration.
"""

from __future__ import annotations

from .convert import convert, convert_async, convert_stream, convert_stream_async
from .options import Options, markdownify_compat

__all__ = [
    "convert",
    "convert_async",
    "convert_stream",
    "convert_stream_async",
    "Options",
    "markdownify_compat",
]

__version__ = "0.0.1"
