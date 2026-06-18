"""Table rules — bounded buffering, header inference, colspan/ragged grids."""

from __future__ import annotations

from html2md import Options, convert


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
