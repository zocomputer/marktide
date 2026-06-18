"""html2text_rs Rust candidate adapter."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Adapter, OptionMap, decode_html


OPTION_MAP = OptionMap(
    settings={"width": 100},
    targets={"width": "use library default wrapping to avoid html2text_rs abort on width=0"},
    residual=(
        "No option surface for markdownify-equivalent image, table, hard-break, or escaping semantics.",
        "Spot-check shows material divergence for code blocks, tables, images, escaping, hard breaks, and link titles.",
    ),
)


@dataclass(frozen=True)
class Html2TextRsAdapter(Adapter):
    name: str = "html2text_rs"
    package: str = "html2text_rs==0.2.5"
    engine: str = "Rust html2text via PyO3"
    option_map: OptionMap = OPTION_MAP

    def convert(self, html_bytes: bytes) -> str:
        import html2text_rs

        return html2text_rs.text_markdown(decode_html(html_bytes), width=100)
