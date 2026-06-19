"""Block + inline handler regression tests.

Drives the committed golden corpus (``block_inline_handler_cases.json``) through the public
``convert`` and asserts byte-equality with the ``markdownify==1.2.2`` oracle output. The
handlers reproduce markdownify's ``convert_*`` functions on the rendered children.

All golden cases pass: the emitter escape/whitespace/boundary pass (141c6b6) and item-D
next-sibling trim (cc46d58) cleared every previously emitter-owned diff.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from marktide import convert

_CORPUS = (
    Path(__file__).resolve().parents[3]
    / "tests" / "conformance" / "golden" / "block_inline_handler_cases.json"
)


def _load_cases() -> list[dict]:
    return json.loads(_CORPUS.read_text(encoding="utf-8"))["cases"]


def _ids(cases: list[dict]) -> list[str]:
    return [c["id"] for c in cases]


_CASES = _load_cases()


@pytest.mark.parametrize("case", _CASES, ids=_ids(_CASES))
def test_block_inline_golden(case: dict) -> None:
    assert convert(case["input_html"]) == case["expected_markdown"]


# --- explicit handler-logic assertions (independent of the corpus) --------------

def test_setext_underline_matches_rendered_text_length() -> None:
    # underline counts the rendered children incl. inline markup, not the source HTML
    assert convert("<h1>Big <b>bold</b></h1>") == "Big **bold**\n============"


def test_atx_headings_h3_to_h6() -> None:
    assert convert("<h3>x</h3>") == "### x"
    assert convert("<h6>x</h6>") == "###### x"


def test_nested_unordered_bullets_cycle_by_depth() -> None:
    md = convert("<ul><li>a<ul><li>b<ul><li>c</li></ul></li></ul></li></ul>")
    assert md == "* a\n  + b\n    - c"


def test_ordered_list_honours_start_attr() -> None:
    assert convert('<ol start="3"><li>three</li><li>four</li></ol>') == "3. three\n4. four"


def test_consecutive_empty_lists_match_markdownify_blank_line_count() -> None:
    # markdownify's convert_list emits '\n\n' + text + ('\n' if before_paragraph else '').
    # An empty list followed by another list has before_paragraph=False (2 newlines); the
    # last one before a paragraph has before_paragraph=True (3 newlines). marktide used to
    # emit a fixed '\n\n\n\n' (4) per empty list, so stacked empty lists (real on the
    # weather.gov nav) accumulated extra blank lines. Counts below are the markdownify oracle.
    assert convert("<p>a</p><ul></ul><ul></ul><p>b</p>") == "a\n\n\n\n\n\n\nb"
    assert convert("<p>a</p><ul></ul><ul></ul><ul></ul><p>b</p>") == "a\n\n\n\n\n\n\n\n\nb"
    assert convert("<p>a</p><ol></ol><ol></ol><p>b</p>") == "a\n\n\n\n\n\n\nb"


def test_single_empty_list_and_edges_unchanged() -> None:
    # Regression guard for the cases that already matched markdownify and must stay matching.
    assert convert("<p>a</p><ul></ul><p>b</p>") == "a\n\n\n\nb"
    assert convert("<p>a</p><ul></ul>") == "a"
    assert convert("<ul></ul><p>b</p>") == "b"
    assert convert("<p>a</p><ul></ul>text<p>b</p>") == "a\n\ntext\n\nb"
    assert convert("<div><ul></ul><ul></ul></div>") == ""


def test_code_span_backtick_fence_grows_and_pads() -> None:
    assert convert("<p><code>a`b</code></p>") == "`` a`b ``"


def test_code_span_commonmark_roundtrip_stable_mode_uses_canonical_delimiters() -> None:
    from marktide import Options

    opts = Options(commonmark_roundtrip_stable=True)
    assert convert("<p><code>a`b</code></p>", options=opts) == "``a`b``"
    assert convert("<p><code>a``b</code></p>", options=opts) == "`a``b`"
    assert convert("<p><code>`lead</code></p>", options=opts) == "`` `lead ``"
    assert convert("<p><code>trail`</code></p>", options=opts) == "`` trail` ``"
    assert convert("<p><code>0</code><code>0</code></p>", options=opts) == "`0``0`"
    assert convert("<p><code>0 </code><code> 0</code></p>", options=opts) == "`0 ` ` 0`"
    assert convert("<p><code> 0 </code></p>", options=opts) == "`  0  `"


def test_br_two_space_hard_break() -> None:
    assert convert("<p>a<br>b</p>") == "a  \nb"


def test_emphasis_option_aware_symbols() -> None:
    assert convert("<p><em>x</em> <strong>y</strong></p>") == "*x* **y**"


def test_empty_inline_is_suppressed() -> None:
    assert convert("<p>a<strong></strong>b</p>") == "ab"


def test_link_inline_and_autolink_shortcut() -> None:
    assert convert('<a href="http://e.com" title="T">t</a>') == '[t](http://e.com "T")'
    assert convert('<a href="http://e.com/p">http://e.com/p</a>') == "<http://e.com/p>"


def test_image_emits_alt_src_title() -> None:
    assert convert('<img src="/i.png" alt="A" title="T">') == '![A](/i.png "T")'


def test_span_is_transparent() -> None:
    assert convert("<p><span>wrap <b>x</b></span></p>") == "wrap **x**"


# --- markdownify Options fidelity (review findings) -----------------------------

def test_paragraph_honours_wrap_width() -> None:
    from marktide import Options

    md = convert("<p>123456789 123456789</p>", options=Options(wrap=True, wrap_width=10))
    assert md == "123456789\n123456789"


def test_pre_honours_code_language_callback() -> None:
    from marktide import Options

    opts = Options(code_language_callback=lambda frame: "python")
    assert convert("<pre>x = 1</pre>", options=opts) == "```python\nx = 1\n```"


def test_strip_pre_strip_one_removes_single_newline() -> None:
    from marktide import Options

    one = convert("<pre>\n\nfoo\n\n</pre>", options=Options(strip_pre="strip_one"))
    full = convert("<pre>\n\nfoo\n\n</pre>", options=Options(strip_pre="strip"))
    assert one == "```\n\nfoo\n```"
    assert full == "```\nfoo\n```"


def test_div_section_article_are_blocks() -> None:
    # markdownify convert_div: block separation, not transparent pass-through
    assert convert("<div><span>Hello</div></span>") == "Hello"
    assert convert("<section>a</section><section>b</section>") == "a\n\nb"
    assert convert("<article>x</article>") == "x"


def test_definition_list() -> None:
    assert convert("<dl><dt>term</dt><dd>definition</dd></dl>") == "term\n:   definition"
    assert (
        convert("<dl><dt>t1</dt><dd>d1</dd><dt>t2</dt><dd>d2</dd></dl>")
        == "t1\n:   d1\n\nt2\n:   d2"
    )


def test_inline_quote_uses_straight_quotes() -> None:
    assert convert("foo <q>quote</q> bar") == 'foo "quote" bar'


def test_script_and_style_are_dropped() -> None:
    assert convert("foo <script>var x=42;</script> bar") == "foo  bar"
    assert convert("foo <style>h1{color:red}</style> bar") == "foo  bar"


def test_figcaption_is_block() -> None:
    md = convert("TEXT<figure><figcaption>Caption</figcaption><span>SPAN</span></figure>")
    assert md == "TEXT\n\nCaption\n\nSPAN"


def test_video_src_poster_and_source_child() -> None:
    assert convert('<video src="/v.mp4" poster="/i.jpg">t</video>') == "[![t](/i.jpg)](/v.mp4)"
    assert convert('<video src="/v.mp4">t</video>') == "[t](/v.mp4)"
    assert convert('<video><source src="/v.mp4"/>t</video>') == "[t](/v.mp4)"
    assert convert('<video poster="/i.jpg">t</video>') == "![t](/i.jpg)"


def test_strikethrough_and_sub_sup_symbols() -> None:
    from marktide import Options

    assert convert("<p><del>x</del></p>") == "~~x~~"
    assert convert("<p><s>x</s></p>") == "~~x~~"
    assert convert("<sub>foo</sub>", options=Options(sub_symbol="~")) == "~foo~"
    assert convert("<sup>foo</sup>", options=Options(sup_symbol="^")) == "^foo^"
    # an HTML-tag-shaped symbol closes with the matching tag
    assert convert("<sub>foo</sub>", options=Options(sub_symbol="<sub>")) == "<sub>foo</sub>"
    # default symbols are empty → plain text passthrough
    assert convert("<p>a<sub>b</sub>c</p>") == "abc"
