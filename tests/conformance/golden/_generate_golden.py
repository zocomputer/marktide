"""Generate the block + inline handler golden corpus: block_inline_handler_cases.json.

This is the **exhaustive per-handler** acceptance set for the block/inline tag groups
(`p`, `h1`-`h6`, `blockquote`, `hr`, `ul`/`ol`/`li`, `strong`/`em`, code spans, `br`, `span`) —
complementary to the cross-cutting §5.3.4 behavior-table set in ``edge_cases.json``. It uses the
**same JSON schema** as ``edge_cases.json`` so a single conformance loader handles both.

Expected Markdown is produced **mechanically** by the pinned oracle ``markdownify==1.2.2`` with
default options (the html2md compatibility contract: underlined h1/h2, ``*`` emphasis, two-space
``<br>``, ``*+-`` depth bullets, ``escape_asterisks``/``escape_underscores`` on, ``escape_misc``
off) — never hand-transcribed. Pure data, no html2md dependency.

Regenerate (must be a no-op unless the oracle pin changes — a reviewed event)::

    python tests/conformance/golden/_generate_golden.py
"""

from __future__ import annotations

import json
from importlib import metadata
from pathlib import Path

from markdownify import markdownify

ORACLE_PIN = "1.2.2"
OUT = Path(__file__).parent / "block_inline_handler_cases.json"

# (id, behavior, markdownify_ref, description, input_html)
CASES: list[tuple[str, str, str, str, str]] = [
    # ---- headings: setext for h1/h2 (underline length == rendered text length), ATX h3-h6 ----
    ("heading_h1_setext", "headings", "convert_hn",
     "h1 renders as a setext underline of '=' matching the text length.",
     "<h1>Title One</h1>"),
    ("heading_h2_setext", "headings", "convert_hn",
     "h2 renders as a setext underline of '-' matching the text length.",
     "<h2>Title Two</h2>"),
    ("heading_h3_atx", "headings", "convert_hn", "h3 uses ATX '###'.", "<h3>Title Three</h3>"),
    ("heading_h4_atx", "headings", "convert_hn", "h4 uses ATX '####'.", "<h4>Title Four</h4>"),
    ("heading_h5_atx", "headings", "convert_hn", "h5 uses ATX '#####'.", "<h5>Title Five</h5>"),
    ("heading_h6_atx", "headings", "convert_hn", "h6 uses ATX '######'.", "<h6>Title Six</h6>"),
    ("heading_h1_inline_underline_len", "headings", "convert_hn",
     "Setext underline length counts the RENDERED text (incl. inline markup chars).",
     "<h1>Big <b>bold</b> and <i>italic</i></h1>"),
    ("heading_h2_unicode_codepoints", "headings", "convert_hn",
     "Setext underline counts Unicode code points, not bytes.",
     "<h2>Café — naïve</h2>"),
    ("heading_h1_leading_trailing_ws", "headings", "convert_hn",
     "Leading/trailing whitespace in a heading is trimmed.",
     "<h1>   spaced   </h1>"),
    ("heading_h3_with_code", "headings", "convert_hn",
     "ATX heading containing an inline code span.",
     "<h3>Use <code>convert()</code> here</h3>"),

    # ---- paragraphs: blank-line separation, whitespace collapse + boundary trim ----
    ("paragraph_simple", "paragraphs", "convert_p", "A single paragraph.",
     "<p>Just a sentence.</p>"),
    ("paragraph_two_blank_line", "paragraphs", "convert_p",
     "Two paragraphs separated by one blank line.", "<p>First.</p><p>Second.</p>"),
    ("paragraph_inline_formatting", "paragraphs", "convert_p",
     "Paragraph with bold and emphasis.", "<p>A <strong>bold</strong> and <em>em</em> word.</p>"),
    ("paragraph_internal_whitespace_run", "paragraphs", "process_text",
     "Internal whitespace runs collapse to a single space.",
     "<p>collapse     these     spaces</p>"),
    ("paragraph_leading_trailing_ws", "paragraphs", "process_text",
     "Leading/trailing whitespace is trimmed at the paragraph boundary.",
     "<p>   trim me   </p>"),
    ("paragraph_source_newlines", "paragraphs", "process_text",
     "Source newlines + indentation collapse to single spaces.",
     "<p>line one\n    line two\n    line three</p>"),

    # ---- blockquote: per-line '> ' prefix, nesting, contained blocks ----
    ("blockquote_simple", "blockquote", "convert_blockquote", "A simple blockquote.",
     "<blockquote>Quoted text.</blockquote>"),
    ("blockquote_two_paragraphs", "blockquote", "convert_blockquote",
     "Blockquote with two paragraphs.",
     "<blockquote><p>Para one.</p><p>Para two.</p></blockquote>"),
    ("blockquote_nested", "blockquote", "convert_blockquote", "Nested blockquote.",
     "<blockquote>Outer <blockquote>Inner</blockquote></blockquote>"),
    ("blockquote_with_list", "blockquote", "convert_blockquote",
     "Blockquote containing a list (each line gets the '> ' prefix).",
     "<blockquote><ul><li>one</li><li>two</li></ul></blockquote>"),
    ("blockquote_with_inline", "blockquote", "convert_blockquote",
     "Blockquote with inline formatting.", "<blockquote>Quote with <b>bold</b>.</blockquote>"),

    # ---- horizontal rule ----
    ("hr_between_paragraphs", "hr", "convert_hr", "hr between two paragraphs.",
     "<p>Above.</p><hr><p>Below.</p>"),
    ("hr_lone", "hr", "convert_hr", "A lone hr.", "<hr>"),

    # ---- lists: nested-list indentation + depth-cycled bullets are the key cases ----
    ("list_ul_flat", "lists", "convert_li", "Flat unordered list.",
     "<ul><li>alpha</li><li>beta</li><li>gamma</li></ul>"),
    ("list_ol_flat", "lists", "convert_li", "Flat ordered list.",
     "<ol><li>one</li><li>two</li><li>three</li></ol>"),
    ("list_ul_nested_three_levels", "lists", "convert_li",
     "Nested unordered list: bullets cycle '*','+','-' by depth with 2-space indents.",
     "<ul><li>top<ul><li>second<ul><li>third</li></ul></li></ul></li></ul>"),
    ("list_ol_nested", "lists", "convert_li", "Nested ordered list.",
     "<ol><li>a<ol><li>a.1</li><li>a.2</li></ol></li><li>b</li></ol>"),
    ("list_mixed_ul_ol", "lists", "convert_li", "Ordered list nested under an unordered item.",
     "<ul><li>bullet<ol><li>num one</li><li>num two</li></ol></li></ul>"),
    ("list_li_inline_formatting", "lists", "convert_li", "List items with inline formatting.",
     "<ul><li>plain</li><li><strong>bold item</strong></li></ul>"),
    ("list_ol_start_attr", "lists", "convert_li", "Ordered list honoring the start attribute.",
     '<ol start="3"><li>three</li><li>four</li></ol>'),
    ("list_ul_multiblock_item", "lists", "convert_li",
     "List item with a second paragraph (continuation indented under the marker).",
     "<ul><li>first<p>second para in item</p></li></ul>"),

    # ---- inline emphasis: strong/em variants, nesting, empty suppression, literal escaping ----
    ("emphasis_strong_tag", "emphasis", "convert_strong", "strong -> **.",
     "<p><strong>strong</strong></p>"),
    ("emphasis_b_tag", "emphasis", "convert_b", "b -> **.", "<p><b>bold</b></p>"),
    ("emphasis_em_tag", "emphasis", "convert_em", "em -> *.", "<p><em>emphasis</em></p>"),
    ("emphasis_i_tag", "emphasis", "convert_i", "i -> *.", "<p><i>italic</i></p>"),
    ("emphasis_nested_strong_em", "emphasis", "convert_strong", "Nested strong/em.",
     "<p><strong>bold <em>and italic</em></strong></p>"),
    ("emphasis_adjacent", "emphasis", "convert_em", "Two adjacent emphasis spans.",
     "<p><em>one</em><em>two</em></p>"),
    ("emphasis_empty_strong_suppressed", "emphasis", "convert_strong",
     "An empty inline emphasis element produces no markup.", "<p>before<strong></strong>after</p>"),
    ("emphasis_literal_chars_escaped", "emphasis", "process_text",
     "Literal '*' and '_' are escaped (escape_asterisks/escape_underscores default on).",
     "<p>a * b _ c</p>"),

    # ---- code spans: backtick-fence growth + space padding (convert_code) ----
    ("code_simple", "code", "convert_code", "A simple inline code span.",
     "<p><code>plain_code</code></p>"),
    ("code_contains_one_backtick", "code", "convert_code",
     "Content with one backtick -> fence grows to '``' with padding spaces.",
     "<p><code>a`b</code></p>"),
    ("code_contains_two_backticks", "code", "convert_code",
     "Content with a double-backtick run -> fence grows past it.", "<p><code>a``b</code></p>"),
    ("code_leading_backtick", "code", "convert_code",
     "Leading backtick -> a padding space is added.", "<p><code>`lead</code></p>"),
    ("code_trailing_backtick", "code", "convert_code",
     "Trailing backtick -> a padding space is added.", "<p><code>trail`</code></p>"),
    ("code_only_backtick", "code", "convert_code", "Content is a single backtick.",
     "<p><code>`</code></p>"),
    ("code_no_escape_inside", "code", "convert_code",
     "Markdown metacharacters inside code are NOT escaped.", "<p><code>*not emphasis*</code></p>"),

    # ---- line breaks: two-space hard break (newline_style default = spaces) ----
    ("br_in_paragraph", "br", "convert_br", "br -> two trailing spaces + newline.",
     "<p>line one<br>line two</p>"),
    ("br_multiple", "br", "convert_br", "Multiple hard breaks.", "<p>a<br>b<br>c</p>"),
    ("br_then_whitespace", "br", "convert_br", "Hard break followed by whitespace then text.",
     "<p>start<br>   end</p>"),

    # ---- span: transparent wrapper, contributes no markup of its own ----
    ("span_plain", "span", "process_tag", "A span is transparent: only its text remains.",
     "<p><span>just text</span></p>"),
    ("span_with_inline_child", "span", "process_tag", "Span wrapping inline formatting.",
     "<p><span>wrap <b>bold</b> here</span></p>"),
    ("span_adjacent", "span", "process_tag", "Adjacent spans.",
     "<p><span>a</span><span>b</span></p>"),
]


def build() -> dict:
    cases = []
    seen: set[str] = set()
    for case_id, behavior, ref, description, html in CASES:
        if case_id in seen:
            raise SystemExit(f"duplicate case id: {case_id}")
        seen.add(case_id)
        cases.append({
            "id": case_id,
            "behavior": behavior,
            "markdownify_ref": ref,
            "description": description,
            "input_html": html,
            "expected_markdown": markdownify(html),
        })
    return {
        "schema_version": 1,
        "purpose": (
            "Exhaustive per-handler block + inline golden fixtures for the html2md handlers "
            "(zo-1fp.12). Same schema as edge_cases.json; complements its cross-cutting "
            "docs/design.md §5.3.4 behavior-table set."
        ),
        "oracle": {
            "package": "markdownify",
            "version": ORACLE_PIN,
            "mode": "library defaults / markdownify_default_oracle semantics",
        },
        "cases": cases,
    }


def main() -> None:
    installed = metadata.version("markdownify")
    if installed != ORACLE_PIN:
        raise SystemExit(
            f"oracle pin mismatch: expected markdownify=={ORACLE_PIN}, found {installed}."
        )
    OUT.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(CASES)} cases)")


if __name__ == "__main__":
    main()
