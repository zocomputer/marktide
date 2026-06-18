"""Table rules: table/thead/tbody/tr/td/th.

Foundation scaffold — handlers filled in by the table-rules task. Tables are the one
construct that buffers: Markdown needs the header row and every cell width before any
row can be emitted (column count + alignment), so a ``<table>`` accumulates into the
bounded :class:`~html2md.state.TableBuffer` (push it onto ``em.state.table_stack`` at
``<table>`` start) and flushes the aligned grid at ``</table>`` (design §4.3, §4.7).
The buffer is bounded by table dimensions, never by document size.

    table        push/pop TableBuffer; flush aligned grid on end
    thead/tbody  toggle TableBuffer.in_header
    tr           start a row
    th/td        accumulate a cell; th sets has_header; align from style/align attr
    Options.table_infer_header  treat first row as header when no thead/th

Register each in ``HANDLERS``.
"""

from __future__ import annotations

from .base import TagHandler

HANDLERS: dict[str, TagHandler] = {}
