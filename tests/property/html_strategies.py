"""Grammar-based HTML generators for bounded property tests."""

from __future__ import annotations

from hypothesis import strategies as st

TEXT_ALPHABET = "abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&<>_*`()[].-/\n\té☕"
SAFE_TEXT = st.text(TEXT_ALPHABET, min_size=0, max_size=40)
URL_TEXT = st.text("abcdefghijklmnopqrstuvwxyz0123456789-_/().?=&", min_size=1, max_size=40)
TAG_NAME = st.sampled_from(["p", "span", "strong", "em", "code", "pre", "blockquote"])


def escaped_text() -> st.SearchStrategy[str]:
    return SAFE_TEXT.map(_escape_html_text)


def inline_html() -> st.SearchStrategy[str]:
    plain = escaped_text()
    entity = st.sampled_from(["&amp;", "&lt;", "&gt;", "&quot;", "&#9731;"])
    code = escaped_text().map(lambda text: f"<code>{text}</code>")
    emphasis = escaped_text().map(lambda text: f"<em>{text}</em>")
    strong = escaped_text().map(lambda text: f"<strong>{text}</strong>")
    link = st.builds(
        lambda href, text: f'<a href="https://example.com/{href}">{text}</a>',
        URL_TEXT.map(_escape_attr),
        escaped_text(),
    )
    image = st.builds(
        lambda src, alt: f'<img src="https://example.com/{src}.png" alt="{alt}">',
        URL_TEXT.map(_escape_attr),
        escaped_text().map(_escape_attr),
    )
    return st.lists(st.one_of(plain, entity, code, emphasis, strong, link, image), min_size=1, max_size=5).map("".join)


def block_html() -> st.SearchStrategy[str]:
    leaf = st.one_of(
        inline_html().map(lambda inner: f"<p>{inner}</p>"),
        inline_html().map(lambda inner: f"<h1>{inner}</h1>"),
        inline_html().map(lambda inner: f"<pre><code>{inner}</code></pre>"),
        st.lists(inline_html(), min_size=1, max_size=4).map(
            lambda items: "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"
        ),
        st.lists(st.tuples(inline_html(), inline_html()), min_size=1, max_size=3).map(_table),
    )
    return st.recursive(
        leaf,
        lambda children: st.one_of(
            st.lists(children, min_size=1, max_size=3).map(lambda parts: "<div>" + "".join(parts) + "</div>"),
            st.lists(children, min_size=1, max_size=3).map(lambda parts: "<section>" + "".join(parts) + "</section>"),
        ),
        max_leaves=8,
    )


def html_document() -> st.SearchStrategy[str]:
    return st.lists(block_html(), min_size=1, max_size=4).map(
        lambda blocks: "<!doctype html><html><body>" + "".join(blocks) + "</body></html>"
    )


def html_fragment_pair() -> st.SearchStrategy[tuple[str, str]]:
    return st.tuples(block_html(), block_html())


def _table(rows: list[tuple[str, str]]) -> str:
    body = "".join(f"<tr><td>{left}</td><td>{right}</td></tr>" for left, right in rows)
    return f"<table>{body}</table>"


def _escape_html_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(value: str) -> str:
    return _escape_html_text(value).replace('"', "&quot;")
