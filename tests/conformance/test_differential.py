import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from differential import Case, load_turndown_cases, normalize_markdown, run_differential, summarize


class FakeAdapter:
    package = "fake"
    engine = "fake"
    option_map = None

    def __init__(self, name: str, suffix: str = "") -> None:
        self.name = name
        self._suffix = suffix

    def convert(self, html_bytes: bytes) -> str:
        text = html_bytes.decode("utf-8")
        return text.replace("<p>", "").replace("</p>", "") + self._suffix


def test_normalize_markdown_policy_level_transforms():
    assert normalize_markdown("a  \r\n\r\n\r\nb\t \n") == "a\n\nb\n"


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
    assert "<p>Hello" in cases[0].html
    assert cases[0].upstream_expected_markdown == "Hello **world**"
    assert cases[0].metadata["data_options"] == '{"headingStyle":"atx"}'


def test_run_differential_compares_candidates_against_default_oracle():
    cases = [Case(id="case:1", layer="unit", source_path="inline", html="<p>Hello</p>")]
    adapters = [
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
    assert summarize(results)["by_adapter"]["candidate_same"]["passed"] == 1
