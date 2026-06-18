"""Table rules — bounded buffering, header inference, colspan/ragged grids."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from markdownify import MarkdownConverter

from marktide import Options, convert


def test_table_th_header_inference() -> None:
    html = (
        "<table><tr><th>Name</th><th>Score</th></tr>"
        "<tr><td>Ada</td><td>10</td></tr></table>"
    )
    assert convert(html) == "\n".join(
        [
            "| Name | Score |",
            "| --- | --- |",
            "| Ada | 10 |",
        ]
    )


def test_table_td_first_row_not_header_without_infer_option() -> None:
    html = (
        "<table><tr><td>Name</td><td>Score</td></tr>"
        "<tr><td>Ada</td><td>10</td></tr></table>"
    )
    assert convert(html) == "\n".join(
        [
            "|  |  |",
            "| --- | --- |",
            "| Name | Score |",
            "| Ada | 10 |",
        ]
    )


def test_table_td_first_row_header_with_infer_option() -> None:
    html = (
        "<table><tr><td>Name</td><td>Score</td></tr>"
        "<tr><td>Ada</td><td>10</td></tr></table>"
    )
    assert convert(html, options=Options(table_infer_header=True)) == "\n".join(
        [
            "| Name | Score |",
            "| --- | --- |",
            "| Ada | 10 |",
        ]
    )


def test_table_colspan_and_ragged_rows() -> None:
    html = (
        "<table><tr><td>Name</td><td colspan='2'>Score</td></tr>"
        "<tr><td>Ada</td><td>10</td><td>11</td></tr>"
        "<tr><td>Bob</td><td>9</td></tr></table>"
    )
    assert convert(html) == "\n".join(
        [
            "|  |  |  |",
            "| --- | --- | --- |",
            "| Name | Score | |",
            "| Ada | 10 | 11 |",
            "| Bob | 9 |",
        ]
    )


def test_table_cell_children_are_rendered_once_and_not_reescaped() -> None:
    html = (
        "<table><tr><th>Markup</th></tr><tr><td><strong>a*b</strong></td></tr></table>"
    )
    assert convert(html) == "\n".join(
        [
            "| Markup |",
            "| --- |",
            "| **a\\*b** |",
        ]
    )


UPSTREAM_TABLE_CASES = (
    "table",
    "table_with_html_content",
    "table_with_paragraphs",
    "table_with_linebreaks",
    "table_with_header_column",
    "table_head_body",
    "table_head_body_missing_head",
    "table_head_body_multiple_head",
    "table_missing_text",
    "table_missing_head",
    "table_body",
    "table_with_caption",
    "table_with_colspan",
    "table_with_undefined_colspan",
    "table_with_colspan_missing_head",
)
_UPSTREAM_TABLES_PATH = Path(
    "tests/conformance/fixtures/markdownify/tests/test_tables.py"
)


def _upstream_table_html(case_name: str) -> str:
    module = ast.parse(_UPSTREAM_TABLES_PATH.read_text())
    for node in module.body:
        if isinstance(node, ast.Assign):
            names = [
                target.id for target in node.targets if isinstance(target, ast.Name)
            ]
            if case_name in names and isinstance(node.value, ast.Constant):
                return str(node.value.value)
    raise AssertionError(f"missing vendored markdownify table case {case_name}")


def _markdownify_md(html: str, **options: object) -> str:
    return MarkdownConverter(strip_document=None, **options).convert(html)


@pytest.mark.parametrize("case_name", UPSTREAM_TABLE_CASES)
@pytest.mark.parametrize("infer_header", [False, True])
def test_vendored_markdownify_table_corpus(case_name: str, infer_header: bool) -> None:
    html = _upstream_table_html(case_name)
    options = {"table_infer_header": infer_header} if infer_header else {}
    expected = _markdownify_md(html, **options)
    actual = convert(
        html, options=Options(strip_document=None, table_infer_header=infer_header)
    )
    assert actual == expected


def test_table_caption_is_preserved_before_grid() -> None:
    html = (
        "TEXT<table><caption>Caption</caption><tbody>"
        "<tr><td>Firstname</td><td>Lastname</td><td>Age</td></tr>"
        "</tbody></table>"
    )
    assert convert(html) == "\n".join(
        [
            "TEXT",
            "",
            "Caption",
            "",
            "|  |  |  |",
            "| --- | --- | --- |",
            "| Firstname | Lastname | Age |",
        ]
    )
    assert convert(html, options=Options(table_infer_header=True)) == "\n".join(
        [
            "TEXT",
            "",
            "Caption",
            "",
            "| Firstname | Lastname | Age |",
            "| --- | --- | --- |",
        ]
    )


def test_multiline_table_cell_whitespace_collapses_to_single_spaces() -> None:
    html = (
        "<table><tr><th>Name</th></tr><tr><td>Smith\n        Jackson</td></tr></table>"
    )
    assert convert(html) == "\n".join(
        [
            "| Name |",
            "| --- |",
            "| Smith Jackson |",
        ]
    )


def test_standalone_table_cell_matches_markdownify_fragment() -> None:
    html = "<td>foo<br />bar</td>"
    assert (
        convert(html, options=Options(strip_document=None, heading_style="atx"))
        == " foo bar |"
    )


def test_standalone_table_row_and_section_match_markdownify_fragments() -> None:
    opts = Options(strip_document=None, heading_style="atx")
    assert convert("<tr><td>foo</td></tr>", options=opts) == "|  |\n| --- |\n| foo |\n"
    assert (
        convert("<tbody><tr><td>foo</td></tr></tbody>", options=opts)
        == "|  |\n| --- |\n| foo |\n"
    )
    assert (
        convert("<thead><tr><td>foo</td></tr></thead>", options=opts)
        == "| foo |\n| --- |\n"
    )
