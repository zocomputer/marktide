"""Kreuzberg html-to-markdown Rust candidate adapter."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Adapter, OptionMap, decode_html


OPTION_MAP = OptionMap(
    settings={
        "heading_style": "atx",
        "code_block_style": "backticks",
        "strong_em_symbol": "*",
        "wrap": False,
    },
    targets={
        "heading_style": "ATX headings",
        "code_block_style": "fenced code blocks",
        "strong_em_symbol": "asterisk emphasis/strong markers",
        "wrap": "avoid line-wrap confound in throughput/fidelity output",
    },
    residual=(
        "May emit reference-style or otherwise normalized links differently from markdownify.",
        "Full semantic distance is reported separately from throughput/GIL metrics.",
    ),
)


@dataclass(frozen=True)
class HtmlToMarkdownAdapter(Adapter):
    name: str = "html_to_markdown"
    package: str = "html-to-markdown==3.5.7"
    engine: str = "Rust html-to-markdown-rs via PyO3"
    option_map: OptionMap = OPTION_MAP

    def convert(self, html_bytes: bytes) -> str:
        import html_to_markdown

        options = _build_options(html_to_markdown)
        result = html_to_markdown.convert(decode_html(html_bytes), options=options)
        content = result.content
        if content is None:
            return ""
        return content


def _build_options(module):
    opts_cls = getattr(module, "ConversionOptions", None)
    if opts_cls is None:
        return None

    kwargs = {
        "heading_style": "atx",
        "code_block_style": "backticks",
        "strong_em_symbol": "*",
        "wrap": False,
    }
    try:
        return opts_cls(**kwargs)
    except TypeError:
        # Older/newer generated bindings may reject one of the normalization
        # kwargs. Fall back to defaults rather than hiding install/API failure.
        supported = {}
        for key, value in kwargs.items():
            try:
                opts_cls(**{key: value})
            except TypeError:
                continue
            supported[key] = value
        return opts_cls(**supported)
