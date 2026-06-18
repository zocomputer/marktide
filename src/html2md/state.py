"""Emitter state — the pushdown stack of the Markdown transducer.

``EmitterState`` is the only state that persists across SAX events. Keeping it to a
bounded stack (open elements) plus O(depth) list/blockquote context plus one bounded
table buffer is exactly what makes conversion a deterministic pushdown transducer and
guarantees chunk-invariance (design §4.3, §9): the output for an event depends only on
the event and this stack, never on how the input bytes were split into feed chunks.

All containers use ``__slots__`` to keep per-conversion overhead low.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Frame:
    """One open element on the stack.

    ``content`` is the element's own output buffer: text and child-element Markdown
    accumulate here while the element is open, so the handler can read the fully
    rendered children at ``end`` (markdownify's ``convert_X(el, text)`` model — needed
    for setext underline length, code-span fence sizing, empty-element suppression).
    ``data`` is free-form per-handler bookkeeping (e.g. a link href captured at
    ``start`` for use at ``end``)."""

    tag: str
    attrs: dict[str, str]
    content: list[str] = field(default_factory=list)
    data: dict[str, object] = field(default_factory=dict)
    # buffering=True: this element wraps/transforms its children, so their Markdown
    # accumulates in `content` until end (bounded by the block). buffering=False:
    # a transparent container that streams children straight through to the nearest
    # buffering ancestor (or the drainable root), so output is not trapped inside an
    # always-open wrapper like the auto-inserted <html>/<body> (design §4.7).
    buffering: bool = True


@dataclass(slots=True)
class ListContext:
    """One level of ``<ul>``/``<ol>`` nesting."""

    ordered: bool
    index: int  # next item number for <ol>; ignored for <ul>
    marker: str  # bullet char for <ul> (chosen by depth from Options.bullets)


@dataclass(slots=True)
class TableCell:
    """One logical Markdown table cell captured from ``<td>`` or ``<th>``.

    ``text`` is already-rendered child Markdown (escaped by the emitter); table rules
    must not re-escape it. ``colspan`` is clamped to markdownify's practical limit so
    malformed input cannot explode the rendered grid.
    """

    tag: str
    text: str
    colspan: int = 1


@dataclass(slots=True)
class TableRow:
    """One captured ``<tr>`` with enough parent metadata to match markdownify.

    Markdownify decides whether a row is a header from both cell tags and parent
    section context (direct table row vs ``thead``/``tbody``/``tfoot``), so rows carry
    their parent section identity plus the row's index within that parent.
    """

    parent_tag: str
    parent_key: int
    parent_order: int
    row_index_in_parent: int
    cells: list[TableCell] = field(default_factory=list)


@dataclass(slots=True)
class TableSection:
    """Open ``thead``/``tbody``/``tfoot`` context for the innermost table."""

    tag: str
    key: int
    order: int


@dataclass(slots=True)
class TableBuffer:
    """Bounded per-table accumulator. Markdown needs the header row before any row can
    be emitted (column count + alignment), so a table is buffered until ``</table>``.
    Bounded by table dimensions, never by document size (design §4.3)."""

    rows: list[TableRow] = field(default_factory=list)
    aligns: list[str | None] = field(default_factory=list)
    in_header: bool = False
    has_header: bool = False
    current_row: TableRow | None = None
    current_cell: TableCell | None = None
    section_stack: list[TableSection] = field(default_factory=list)
    parent_row_counts: dict[int, int] = field(default_factory=dict)
    next_parent_key: int = 1
    next_section_order: int = 1
    has_thead: bool = False


class EmitterState:
    """Mutable conversion state. Owned by :class:`~html2md.emitter.MarkdownEmitter`;
    rule handlers read and mutate it through the emitter context."""

    __slots__ = (
        "stack",  # list[Frame] — open elements (pushdown stack)
        "list_stack",  # list[ListContext] — nested list context
        "blockquote_depth",  # int — number of "> " prefixes
        "pre_depth",  # int — >0 means verbatim text (no escape/collapse)
        "table_stack",  # list[TableBuffer] — nested tables (rare but legal)
        "pending",  # list[str] — uncommitted inline lookahead buffer
    )

    def __init__(self) -> None:
        self.stack: list[Frame] = []
        self.list_stack: list[ListContext] = []
        self.blockquote_depth: int = 0
        self.pre_depth: int = 0
        self.table_stack: list[TableBuffer] = []
        self.pending: list[str] = []

    # --- open-element stack ---------------------------------------------------

    def push(self, tag: str, attrs: dict[str, str]) -> Frame:
        frame = Frame(tag=tag, attrs=attrs)
        self.stack.append(frame)
        return frame

    def pop(self) -> Frame | None:
        return self.stack.pop() if self.stack else None

    @property
    def top(self) -> Frame | None:
        return self.stack[-1] if self.stack else None

    @property
    def depth(self) -> int:
        return len(self.stack)

    # --- context predicates ---------------------------------------------------

    @property
    def in_pre(self) -> bool:
        return self.pre_depth > 0

    @property
    def in_table(self) -> bool:
        return bool(self.table_stack)

    def has_ancestor(self, *tags: str) -> bool:
        """True if any open element matches one of ``tags`` (markdownify-style
        ``parent_tags`` membership used by inline/whitespace rules)."""
        return any(frame.tag in tags for frame in self.stack)
