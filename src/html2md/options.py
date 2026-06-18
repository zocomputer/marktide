"""Conversion options — a faithful typed mirror of ``markdownify==1.2.2``.

Every field name and default here is identical to
``markdownify.MarkdownConverter.DefaultOptions`` (verified against
``.venv/lib/python3.12/site-packages/markdownify/__init__.py``), which is what makes
the drop-in claim real and the conformance oracle exact. Two html2md-specific fields
(``chunk_size``, ``default_encoding``) have no markdownify equivalent.

``markdownify_compat(**md_kwargs)`` is the migration contract: it accepts every
markdownify keyword and maps it onto the identical field, rejecting the two things
html2md cannot honour (``bs4_options`` — we drive lxml, not BeautifulSoup) and the
markdownify ``strip``/``convert`` mutual-exclusion.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields
from typing import Any, Literal

HeadingStyle = Literal["underlined", "atx", "atx_closed"]
NewlineStyle = Literal["spaces", "backslash"]
StripMode = Literal["strip", "lstrip", "rstrip"]


@dataclass(frozen=True, slots=True)
class Options:
    """Immutable conversion options. Defaults match ``markdownify==1.2.2`` exactly."""

    # --- markdownify==1.2.2 options: names + defaults are IDENTICAL ---
    autolinks: bool = True
    bullets: str = "*+-"  # iterable of markers; nested <ul> picks by depth
    code_language: str = ""
    # markdownify passes a bs4 Tag; html2md has no bs4 dependency, so the callback
    # receives html2md's own element view. Typed loosely to avoid a bs4 import.
    code_language_callback: Callable[[Any], str] | None = None
    convert: tuple[str, ...] | None = None  # allowlist of tags to convert;
    strip: tuple[str, ...] | None = None    #   mutually exclusive with `convert`
    default_title: bool = False
    escape_asterisks: bool = True
    escape_underscores: bool = True
    escape_misc: bool = False  # markdownify default is False (not True)
    heading_style: HeadingStyle = "underlined"  # setext h1/h2 by default
    keep_inline_images_in: tuple[str, ...] = ()
    newline_style: NewlineStyle = "spaces"  # <br> → two trailing spaces
    strip_document: StripMode | None = "strip"
    strip_pre: StripMode | None = "strip"
    strong_em_symbol: Literal["*", "_"] = "*"
    sub_symbol: str = ""
    sup_symbol: str = ""
    table_infer_header: bool = False
    wrap: bool = False
    wrap_width: int = 80

    # --- html2md-specific (no markdownify equivalent) ---
    chunk_size: int = 64 * 1024  # feed granularity; empirical default (design §4.2)
    default_encoding: str = "utf-8"

    def __post_init__(self) -> None:
        # markdownify raises when both tag filters are given (MarkdownConverter.__init__).
        if self.strip is not None and self.convert is not None:
            raise ValueError(
                "strip and convert are mutually exclusive (matching markdownify); "
                "pass at most one"
            )


# markdownify keywords that html2md deliberately does not support.
_UNSUPPORTED = {
    "bs4_options": (
        "bs4_options is not supported: html2md uses lxml, not BeautifulSoup; "
        "remove this kwarg"
    ),
}

# markdownify keywords whose value is an iterable that we normalise to a tuple so
# Options stays hashable/frozen.
_TUPLE_FIELDS = {"convert", "strip", "keep_inline_images_in"}

_OPTION_FIELDS = frozenset(f.name for f in fields(Options))


def markdownify_compat(**md_kwargs: Any) -> Options:
    """Build an :class:`Options` from ``markdownify==1.2.2`` keyword arguments.

    Accepts every markdownify option under its identical name. Raises ``ValueError``
    on ``bs4_options`` (unsupported) and on the markdownify ``strip``/``convert``
    mutual-exclusion (enforced by ``Options.__post_init__``). Unknown keywords raise
    ``TypeError``, matching a normal constructor call.
    """
    for key in md_kwargs:
        if key in _UNSUPPORTED:
            raise ValueError(_UNSUPPORTED[key])
        if key not in _OPTION_FIELDS:
            raise TypeError(f"markdownify_compat() got an unexpected keyword argument {key!r}")

    normalised = {
        key: (tuple(value) if key in _TUPLE_FIELDS and value is not None else value)
        for key, value in md_kwargs.items()
    }
    return Options(**normalised)
