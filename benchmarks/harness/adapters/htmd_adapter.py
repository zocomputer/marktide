"""htmd-py Rust candidate adapter."""

from __future__ import annotations

from dataclasses import dataclass

from .base import Adapter, OptionMap, decode_html


OPTION_MAP = OptionMap(
    settings={
        "heading_style": "ATX",
        "bullet_list_marker": "ASTERISK",
        "code_block_style": "FENCED",
        "br_style": "TWO_SPACES",
    },
    targets={
        "heading_style": "ATX headings",
        "bullet_list_marker": "stable unordered-list marker",
        "code_block_style": "fenced code blocks",
        "br_style": "markdownify-compatible hard breaks where supported",
    },
    residual=(
        "htmd-py's option surface differs from markdownify; unsupported contract dimensions are scored as residual semantic divergence.",
    ),
)


@dataclass(frozen=True)
class HtmdAdapter(Adapter):
    name: str = "htmd_py"
    package: str = "htmd-py==0.1.2"
    engine: str = "Rust htmd via PyO3"
    option_map: OptionMap = OPTION_MAP

    def convert(self, html_bytes: bytes) -> str:
        import htmd

        return htmd.convert_html(decode_html(html_bytes), _build_options(htmd))


def _set_if_present(obj, attr: str, value) -> None:
    if hasattr(obj, attr):
        setattr(obj, attr, value)


def _enum_value(module, enum_name: str, member_name: str, fallback: str):
    enum_obj = getattr(module, enum_name, None)
    return getattr(enum_obj, member_name, fallback) if enum_obj is not None else fallback


def _build_options(module):
    options = module.Options()
    _set_if_present(options, "heading_style", _enum_value(module, "HeadingStyle", "ATX", "atx"))
    _set_if_present(options, "bullet_list_marker", _enum_value(module, "BulletListMarker", "ASTERISK", "asterisk"))
    _set_if_present(options, "code_block_style", _enum_value(module, "CodeBlockStyle", "FENCED", "fenced"))
    _set_if_present(options, "br_style", _enum_value(module, "BrStyle", "TWO_SPACES", "two_spaces"))
    return options
