import json
import sys
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmarks.harness.adapters.base import Adapter, OptionMap  # noqa: E402

from differential import (  # noqa: E402
    Case,
    commonmark_semantic_equal,
    load_golden_cases,
    load_markdownify_cases,
    load_turndown_cases,
    normalize_markdown,
    run_differential,
    summarize,
)


class FakeAdapter:
    package = "fake"
    engine = "fake"
    option_map = OptionMap()

    def __init__(self, name: str, suffix: str = "") -> None:
        self.name = name
        self._suffix = suffix

    def convert(self, html_bytes: bytes) -> str:
        text = html_bytes.decode("utf-8")
        return text.replace("<p>", "").replace("</p>", "") + self._suffix


class StaticAdapter:
    package = "fake"
    engine = "fake"
    option_map = OptionMap()

    def __init__(self, name: str, output: str) -> None:
        self.name = name
        self._output = output

    def convert(self, html_bytes: bytes) -> str:
        return self._output


def test_normalize_markdown_policy_level_transforms():
    # CRLF folded, document edges stripped, runs of 3+ blank lines collapsed to one,
    # exactly one trailing newline. Interior trailing whitespace ("a  ") is preserved
    # so a mid-document dropped space surfaces as a real divergence rather than being
    # equalized away by the comparator.
    assert normalize_markdown("a  \r\n\r\n\r\nb\t \n") == "a  \n\nb\n"


def test_normalize_markdown_preserves_interior_trailing_whitespace():
    # Regression guard: the per-line rstrip that used to live here masked the
    # passthrough-inline trailing-space bug. A trailing space before an interior
    # newline must NOT be normalized away.
    assert normalize_markdown("foo \nbar") == "foo \nbar\n"
    assert normalize_markdown("foo\nbar") == "foo\nbar\n"


def test_load_turndown_cases_from_attendant_html(tmp_path: Path):
    fixture = tmp_path / "turndown" / "test"
    fixture.mkdir(parents=True)
    (fixture / "index.html").write_text(
        """
        <html><body>
        <div class="case" data-name="p case" data-options='{"headingStyle":"atx"}'>
          <div class="input"><p>Hello <strong>world</strong></p></div>
          <pre class="expected">Hello **world**</pre>
        </div>
        </body></html>
        """,
        encoding="utf-8",
    )
    cases = load_turndown_cases(tmp_path)
    assert len(cases) == 1
    assert cases[0].id == "turndown:0000:p-case"
    assert cases[0].layer == "turndown_options"
    assert "<p>Hello" in cases[0].html
    assert cases[0].upstream_expected_markdown == "Hello **world**"
    assert cases[0].metadata["data_options"] == '{"headingStyle":"atx"}'


def test_load_golden_cases_globs_oracle_schema_and_skips_negative_schema(tmp_path: Path):
    golden = tmp_path / "golden"
    fixtures = tmp_path / "fixtures"
    golden.mkdir()
    fixtures.mkdir()
    (golden / "edge_cases.json").write_text(
        json.dumps({
            "schema_version": 1,
            "cases": [
                {
                    "id": "x",
                    "behavior": "b",
                    "markdownify_ref": "ref",
                    "description": "d",
                    "input_html": "<p>x</p>",
                    "expected_markdown": "x",
                }
            ],
        }),
        encoding="utf-8",
    )
    (golden / "normalizer_negative_cases.json").write_text(
        json.dumps({
            "schema_version": 1,
            "cases": [{"id": "neg", "left_markdown": "*x*", "right_markdown": r"\*x\*"}],
        }),
        encoding="utf-8",
    )

    cases = load_golden_cases(fixtures)

    assert [case.id for case in cases] == ["golden:edge_cases:x"]
    assert cases[0].layer == "golden"
    assert cases[0].html == "<p>x</p>"
    assert cases[0].upstream_expected_markdown == "x"


def test_load_markdownify_cases_captures_md_options_and_excludes_custom_converter(tmp_path: Path):
    tests_root = tmp_path / "markdownify" / "tests"
    tests_root.mkdir(parents=True)
    (tests_root / "test_conversions.py").write_text(
        """
from markdownify import ATX, BACKSLASH
from .utils import md

def test_options():
    assert md('<h1>x</h1>', heading_style=ATX, newline_style=BACKSLASH, wrap_width=None, keep_inline_images_in=['h3']) == '# x'
""",
        encoding="utf-8",
    )
    (tests_root / "test_custom_converter.py").write_text(
        """
from .utils import md

def test_custom():
    assert md('<h1>x</h1>') == 'custom'
""",
        encoding="utf-8",
    )

    cases = load_markdownify_cases(tmp_path)

    assert [case.id for case in cases] == ["markdownify:test_conversions:6"]
    assert cases[0].upstream_expected_markdown == "# x"
    assert cases[0].metadata["markdownify_options"] == {
        "strip_document": None,
        "heading_style": "atx",
        "newline_style": "backslash",
        "wrap_width": None,
        "keep_inline_images_in": ["h3"],
    }


def test_run_differential_compares_candidates_against_default_oracle():
    cases = [Case(id="case:1", layer="unit", source_path="inline", html="<p>Hello</p>")]
    adapters: list[Adapter] = [
        FakeAdapter("markdownify_default_oracle"),
        FakeAdapter("markdownify", suffix=" normalized"),
        FakeAdapter("candidate_same"),
        FakeAdapter("candidate_diff", suffix=" different"),
    ]
    results = run_differential(cases, adapters)
    by_name = {result.adapter: result for result in results[0].results}
    assert "markdownify" not in by_name
    assert by_name["candidate_same"].passed is True
    assert by_name["candidate_diff"].passed is False
    assert "different" in (by_name["candidate_diff"].diff or "")
    summary = summarize(results)
    by_adapter = cast(dict[str, dict[str, int]], summary["by_adapter"])
    assert by_adapter["candidate_same"]["passed"] == 1


def test_commonmark_layer_compares_rendered_semantic_html():
    cases = [Case(id="commonmark:semantic", layer="commonmark_expected_html", source_path="inline", html="<p>x</p>")]
    adapters: list[Adapter] = [
        StaticAdapter("markdownify_default_oracle", "*x*"),
        StaticAdapter("candidate_same_html", "_x_"),
    ]

    results = run_differential(cases, adapters)

    assert results[0].results[0].passed is True
    assert commonmark_semantic_equal("x\n", "x\n\n") is True


def test_primary_markdownify_summary_is_separate_from_guardrail_layers():
    cases = [
        Case(id="golden:1", layer="golden", source_path="inline", html="<p>a</p>"),
        Case(id="commonmark:1", layer="commonmark_expected_html", source_path="inline", html="<p>b</p>"),
    ]
    adapters: list[Adapter] = [
        FakeAdapter("markdownify_default_oracle"),
        FakeAdapter("candidate_same"),
    ]

    summary = summarize(run_differential(cases, adapters))

    assert summary["primary_markdownify_layers"] == ["golden", "markdownify_tests"]
    primary_counts = cast(dict[str, dict[str, int]], summary["primary_markdownify_oracle"])
    by_adapter = cast(dict[str, dict[str, int]], summary["by_adapter"])
    assert primary_counts["candidate_same"]["passed"] == 1
    assert by_adapter["candidate_same"]["passed"] == 2
