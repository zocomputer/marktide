"""Adapter protocol and registry for phase-1 HTML→Markdown benchmarks."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Iterable
from typing import Callable, Protocol


@dataclass(frozen=True)
class OptionMap:
    """Documents apples-to-apples option choices for one benchmark adapter.

    ``settings`` stores concrete native kwargs/attributes used by the adapter.
    ``targets`` maps each setting to the markdownify-compatible contract dimension
    it is intended to normalize (heading style, fenced code, hard breaks, etc.).
    ``residual`` lists known semantic differences that cannot be normalized via the
    candidate library's public option surface.
    """

    settings: dict[str, object] = field(default_factory=dict)
    targets: dict[str, str] = field(default_factory=dict)
    residual: tuple[str, ...] = ()


class Adapter(Protocol):
    """Uniform benchmark interface for all HTML→Markdown candidates."""

    name: str
    package: str
    engine: str
    option_map: OptionMap

    def convert(self, html_bytes: bytes) -> str:
        """Convert UTF-8 HTML bytes to Markdown text."""


class StreamingAdapter(Adapter, Protocol):
    """Adapter with a native streaming conversion path for TTFO/cadence rows."""

    def convert_stream_chunks(self, html_bytes: bytes) -> Iterable[str]:
        """Yield Markdown chunks from the adapter's streaming API."""


def supports_streaming(adapter: Adapter) -> bool:
    """Return True when an adapter exposes a native streaming conversion path."""

    return callable(getattr(adapter, "convert_stream_chunks", None))


def decode_html(html_bytes: bytes) -> str:
    """Decode benchmark fixture bytes using the phase-1 UTF-8 fixture contract."""

    return html_bytes.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class AdapterSpec:
    name: str
    factory: Callable[[], Adapter]


def get_adapter_specs(include_lxml_naive: bool = True) -> list[AdapterSpec]:
    """Return phase-1 adapter factories in stable report order."""

    from .html2md_adapter import Html2MdAdapter, Html2MdStreamingAdapter
    from .html2text_rs_adapter import Html2TextRsAdapter
    from .html_to_markdown_adapter import HtmlToMarkdownAdapter
    from .htmd_adapter import HtmdAdapter
    from .markdownify_adapter import MarkdownifyAdapter, MarkdownifyDefaultOracleAdapter

    specs: list[AdapterSpec] = [
        AdapterSpec("markdownify", MarkdownifyAdapter),
        AdapterSpec("markdownify_default_oracle", MarkdownifyDefaultOracleAdapter),
        AdapterSpec("html_to_markdown", HtmlToMarkdownAdapter),
        AdapterSpec("htmd_py", HtmdAdapter),
        AdapterSpec("html2text_rs", Html2TextRsAdapter),
        AdapterSpec("html2md", Html2MdAdapter),
        AdapterSpec("html2md_streaming", Html2MdStreamingAdapter),
    ]
    if include_lxml_naive:
        from .lxml_naive_adapter import LxmlNaiveAdapter

        specs.append(AdapterSpec("lxml_naive", LxmlNaiveAdapter))
    return specs


def get_adapters(include_lxml_naive: bool = True) -> list[Adapter]:
    """Instantiate all configured phase-1 adapters."""

    return [
        spec.factory()
        for spec in get_adapter_specs(include_lxml_naive=include_lxml_naive)
    ]
