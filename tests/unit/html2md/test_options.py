"""Options defaults + markdownify_compat mapping — exact markdownify==1.2.2 parity."""

from __future__ import annotations

import pytest
from markdownify import MarkdownConverter

from html2md.options import Options, markdownify_compat

# markdownify options that html2md does not mirror as a field.
_MD_ONLY = {"bs4_options"}
_ITERABLE_FIELDS = {"convert", "strip", "keep_inline_images_in", "bullets"}


def _norm(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


def _md_defaults() -> dict[str, object]:
    d = MarkdownConverter.DefaultOptions
    return {k: getattr(d, k) for k in dir(d) if not k.startswith("_")}


def test_defaults_match_markdownify_field_for_field() -> None:
    opts = Options()
    for name, md_default in _md_defaults().items():
        if name in _MD_ONLY:
            continue
        assert hasattr(opts, name), f"Options missing markdownify field {name!r}"
        assert _norm(getattr(opts, name)) == _norm(md_default), f"default mismatch: {name}"


def test_html2md_specific_defaults() -> None:
    opts = Options()
    assert opts.chunk_size == 64 * 1024
    assert opts.default_encoding == "utf-8"
    assert opts.commonmark_roundtrip_stable is False


def test_options_is_frozen_and_hashable() -> None:
    opts = Options()
    with pytest.raises(Exception):
        opts.wrap = True  # type: ignore[misc]
    assert hash(opts) == hash(Options())


# --- markdownify_compat: one acceptance case per markdownify option ----------

_ACCEPT_CASES: dict[str, object] = {
    "autolinks": False,
    "bullets": "-",
    "code_language": "python",
    "convert": ["a", "b"],
    "default_title": True,
    "escape_asterisks": False,
    "escape_underscores": False,
    "escape_misc": True,
    "heading_style": "atx",
    "keep_inline_images_in": ["td"],
    "newline_style": "backslash",
    "strip": ["i"],
    "strip_document": "lstrip",
    "strip_pre": "rstrip",
    "strong_em_symbol": "_",
    "sub_symbol": "~",
    "sup_symbol": "^",
    "table_infer_header": True,
    "wrap": True,
    "wrap_width": 100,
}


@pytest.mark.parametrize("name,value", list(_ACCEPT_CASES.items()))
def test_markdownify_compat_maps_each_option(name: str, value: object) -> None:
    opts = markdownify_compat(**{name: value})
    assert getattr(opts, name) == _norm(value)


def test_markdownify_compat_code_language_callback() -> None:
    def cb(_el: object) -> str:
        return "rust"

    assert markdownify_compat(code_language_callback=cb).code_language_callback is cb


def test_compat_covers_every_markdownify_option() -> None:
    # Guard: the acceptance table stays exhaustive as markdownify evolves.
    md_options = set(_md_defaults()) - _MD_ONLY
    covered = set(_ACCEPT_CASES) | {"code_language_callback"}
    assert md_options <= covered, f"untested markdownify options: {md_options - covered}"


# --- rejections (exact messages from design §6.3) ----------------------------

def test_bs4_options_rejected() -> None:
    with pytest.raises(ValueError, match="bs4_options is not supported"):
        markdownify_compat(bs4_options="html.parser")


def test_strip_and_convert_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        markdownify_compat(strip=["a"], convert=["b"])
    with pytest.raises(ValueError, match="mutually exclusive"):
        Options(strip=("a",), convert=("b",))


def test_unknown_option_raises_typeerror() -> None:
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        markdownify_compat(not_a_real_option=1)
