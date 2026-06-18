"""markdownify incumbent adapter."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Adapter, OptionMap, decode_html


OPTION_MAP = OptionMap(
    settings={
        "heading_style": "ATX",
        "bullets": "*",
        "strong_em_symbol": "ASTERISK",
        "code_language": "",
    },
    targets={
        "heading_style": "ATX headings for comparability with Rust candidates",
        "bullets": "stable unordered-list marker",
        "strong_em_symbol": "asterisk emphasis/strong markers",
        "code_language": "do not inject synthetic code fence language",
    },
    residual=(
        "This is the incumbent oracle; residual divergences are assigned to other adapters.",
    ),
)


@dataclass(frozen=True)
class MarkdownifyAdapter(Adapter):
    name: str = "markdownify"
    package: str = "markdownify>=0.13 + beautifulsoup4"
    engine: str = "BeautifulSoup / pure Python"
    option_map: OptionMap = OPTION_MAP

    def convert(self, html_bytes: bytes) -> str:
        from markdownify import ATX, ASTERISK, markdownify

        return markdownify(
            decode_html(html_bytes),
            heading_style=ATX,
            bullets="*",
            strong_em_symbol=ASTERISK,
            code_language="",
        )
