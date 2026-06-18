"""Naive lxml baseline adapter: C parse plus Python tree walk/emission."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree

from .base import Adapter, OptionMap


OPTION_MAP = OptionMap(
    settings={"parser": "etree.HTMLParser(recover=True, huge_tree=True)"},
    targets={"parser": "large malformed HTML fixture compatibility"},
    residual=(
        "Intentionally naive Markdown semantics; establishes lxml parse + Python walk performance/GIL baseline only.",
    ),
)


@dataclass(frozen=True)
class LxmlNaiveAdapter(Adapter):
    name: str = "lxml_naive"
    package: str = "lxml>=5.0"
    engine: str = "libxml2 parse + Python tree walk"
    option_map: OptionMap = OPTION_MAP

    def convert(self, html_bytes: bytes) -> str:
        root = etree.fromstring(html_bytes, etree.HTMLParser(recover=True, huge_tree=True))
        out: list[str] = []
        _emit_node(root, out)
        return "".join(out).strip() + "\n"


def _text(text: str | None) -> str:
    return text or ""


def _emit_node(node, out: list[str]) -> None:
    tag = node.tag.lower() if isinstance(node.tag, str) else ""
    if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        out.append("#" * int(tag[1]) + " ")
    elif tag == "li":
        out.append("- ")
    elif tag in {"strong", "b"}:
        out.append("**")
    elif tag in {"em", "i"}:
        out.append("*")
    elif tag == "br":
        out.append("  \n")

    if node.text:
        out.append(_text(node.text))
    for child in node:
        _emit_node(child, out)
        if child.tail:
            out.append(_text(child.tail))

    if tag in {"strong", "b"}:
        out.append("**")
    elif tag in {"em", "i"}:
        out.append("*")
    elif tag in {"p", "div", "section", "article", "li", "ul", "ol"} or tag.startswith("h"):
        out.append("\n")
