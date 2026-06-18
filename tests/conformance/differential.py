"""Conformance differential harness for HTML→Markdown candidates.

Runs staged corpus cases through the shared benchmark adapter layer and compares
candidate output against the incumbent markdownify default-semantics adapter as the oracle. Reports
per-fixture pass/fail plus bounded unified diffs.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lxml import html as lxml_html

from benchmarks.harness.adapters.base import Adapter, get_adapters

DEFAULT_FIXTURE_ROOT = REPO_ROOT / "tests" / "conformance" / "fixtures"
DEFAULT_REPORT_DIR = REPO_ROOT / "tests" / "conformance" / "reports"


@dataclass(frozen=True)
class Case:
    id: str
    layer: str
    source_path: str
    html: str
    upstream_expected_markdown: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateResult:
    adapter: str
    passed: bool
    error: str | None
    output_sha256: str | None
    normalized_output_sha256: str | None
    diff: str | None


@dataclass(frozen=True)
class CaseResult:
    id: str
    layer: str
    source_path: str
    input_bytes: int
    oracle_sha256: str
    normalized_oracle_sha256: str
    results: list[CandidateResult]
    metadata: dict[str, object] = field(default_factory=dict)


def normalize_markdown(text: str) -> str:
    """Apply policy-level normalization from tests/conformance/sources.toml."""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    text = "\n".join(lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text + "\n" if text else ""


def sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def bounded_unified_diff(expected: str, actual: str, *, max_chars: int = 4000) -> str:
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile="markdownify_oracle.md",
            tofile="candidate.md",
            n=3,
        )
    )
    if len(diff) > max_chars:
        return diff[:max_chars] + f"\n... diff truncated at {max_chars} chars ...\n"
    return diff


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _inner_html(element) -> str:
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        parts.append(lxml_html.tostring(child, encoding="unicode", method="html"))
    return "".join(parts)


def load_turndown_cases(root: Path = DEFAULT_FIXTURE_ROOT) -> list[Case]:
    path = root / "turndown" / "test" / "index.html"
    document = lxml_html.fromstring(path.read_text(encoding="utf-8"))
    cases = []
    for index, case_el in enumerate(document.xpath("//div[contains(concat(' ', normalize-space(@class), ' '), ' case ')]")):
        name = case_el.get("data-name") or f"case-{index}"
        input_nodes = case_el.xpath(".//div[contains(concat(' ', normalize-space(@class), ' '), ' input ')]")
        if not input_nodes:
            continue
        expected_nodes = case_el.xpath(".//pre[contains(concat(' ', normalize-space(@class), ' '), ' expected ')]")
        cases.append(
            Case(
                id=f"turndown:{index:04d}:{_slug(name)}",
                layer="turndown",
                source_path=_display_path(path),
                html=_inner_html(input_nodes[0]),
                upstream_expected_markdown=expected_nodes[0].text if expected_nodes else None,
                metadata={"name": name, "data_options": case_el.get("data-options")},
            )
        )
    return cases


def load_pandoc_cases(root: Path = DEFAULT_FIXTURE_ROOT) -> list[Case]:
    base = root / "pandoc"
    cases = []
    for path in sorted((base / "test").rglob("*.html")):
        cases.append(
            Case(
                id=f"pandoc:{_slug(str(path.relative_to(base)))}",
                layer="pandoc",
                source_path=_display_path(path),
                html=path.read_text(encoding="utf-8", errors="replace"),
            )
        )
    return cases


def load_commonmark_cases(root: Path = DEFAULT_FIXTURE_ROOT) -> list[Case]:
    path = root / "commonmark-spec" / "spec.txt"
    text = path.read_text(encoding="utf-8")
    fence = "`" * 32
    pattern = re.compile(rf"^{fence} example\n(.*?)\n\.\n(.*?)\n{fence}$", re.M | re.S)
    cases = []
    for index, match in enumerate(pattern.finditer(text)):
        markdown_input = match.group(1).replace("→", "\t")
        expected_html = match.group(2).replace("→", "\t")
        cases.append(
            Case(
                id=f"commonmark:{index + 1:04d}",
                layer="commonmark_expected_html",
                source_path=_display_path(path),
                html=expected_html,
                upstream_expected_markdown=markdown_input,
                metadata={"commonmark_example_number": index + 1},
            )
        )
    return cases


def load_golden_cases(root: Path = DEFAULT_FIXTURE_ROOT) -> list[Case]:
    """Load hand-authored markdownify-oracle golden cases from golden/*.json.

    Golden files can be added by multiple agents without central registration. A
    file is considered an oracle golden file when every loaded case has
    ``input_html`` and ``expected_markdown`` fields. Files such as
    ``normalizer_negative_cases.json`` deliberately use different fields and are
    skipped by this loader.
    """

    golden_root = root.parent / "golden"
    if not golden_root.exists():
        return []
    cases: list[Case] = []
    for path in sorted(golden_root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_cases = payload.get("cases", [])
        if not isinstance(raw_cases, list):
            continue
        for index, raw_case in enumerate(raw_cases):
            if not isinstance(raw_case, dict):
                continue
            input_html = raw_case.get("input_html")
            expected = raw_case.get("expected_markdown")
            if not isinstance(input_html, str) or not isinstance(expected, str):
                continue
            case_id = str(raw_case.get("id") or f"{path.stem}:{index}")
            cases.append(
                Case(
                    id=f"golden:{path.stem}:{case_id}",
                    layer="golden",
                    source_path=_display_path(path),
                    html=input_html,
                    upstream_expected_markdown=expected,
                    metadata={
                        "golden_file": path.name,
                        "behavior": raw_case.get("behavior"),
                        "markdownify_ref": raw_case.get("markdownify_ref"),
                        "description": raw_case.get("description"),
                    },
                )
            )
    return cases


def load_markdownify_cases(root: Path = DEFAULT_FIXTURE_ROOT) -> list[Case]:
    base = root / "markdownify" / "tests"
    cases: list[Case] = []
    for path in sorted(base.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue
            extracted = _extract_md_assert(node.test)
            if extracted is None:
                continue
            html_input, expected = extracted
            line = getattr(node, "lineno", 0)
            cases.append(
                Case(
                    id=f"markdownify:{path.stem}:{line}",
                    layer="markdownify_tests",
                    source_path=_display_path(path),
                    html=html_input,
                    upstream_expected_markdown=expected,
                    metadata={"line": line},
                )
            )
    return cases


def _extract_md_assert(expr: ast.expr) -> tuple[str, str] | None:
    if not isinstance(expr, ast.Compare) or len(expr.ops) != 1 or not isinstance(expr.ops[0], ast.Eq):
        return None
    if len(expr.comparators) != 1:
        return None
    left = expr.left
    right = expr.comparators[0]
    if not isinstance(left, ast.Call):
        return None
    if isinstance(left.func, ast.Name):
        fn_name = left.func.id
    elif isinstance(left.func, ast.Attribute):
        fn_name = left.func.attr
    else:
        return None
    if fn_name != "md" or not left.args:
        return None
    if not isinstance(left.args[0], ast.Constant) or not isinstance(left.args[0].value, str):
        return None
    if not isinstance(right, ast.Constant) or not isinstance(right.value, str):
        return None
    return left.args[0].value, right.value


def _slug(value: str) -> str:
    value = value.lower().replace("/", "_").replace(".", "_")
    value = re.sub(r"[^a-z0-9_-]+", "-", value).strip("-")
    return value[:120] or "case"


def load_cases(root: Path = DEFAULT_FIXTURE_ROOT) -> list[Case]:
    return [
        *load_golden_cases(root),
        *load_markdownify_cases(root),
        *load_turndown_cases(root),
        *load_pandoc_cases(root),
        *load_commonmark_cases(root),
    ]


def run_differential(cases: Iterable[Case], adapters: list[Adapter], *, max_diff_chars: int = 4000) -> list[CaseResult]:
    oracle = next(adapter for adapter in adapters if adapter.name == "markdownify_default_oracle")
    candidates = [adapter for adapter in adapters if not adapter.name.startswith("markdownify")]
    results: list[CaseResult] = []
    for case in cases:
        html_bytes = case.html.encode("utf-8", errors="replace")
        oracle_output = oracle.convert(html_bytes)
        normalized_oracle = normalize_markdown(oracle_output)
        candidate_results: list[CandidateResult] = []
        for adapter in candidates:
            try:
                output = adapter.convert(html_bytes)
                normalized = normalize_markdown(output)
                passed = normalized == normalized_oracle
                candidate_results.append(
                    CandidateResult(
                        adapter=adapter.name,
                        passed=passed,
                        error=None,
                        output_sha256=sha256_text(output),
                        normalized_output_sha256=sha256_text(normalized),
                        diff=None if passed else bounded_unified_diff(normalized_oracle, normalized, max_chars=max_diff_chars),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - reports should capture converter failures
                candidate_results.append(
                    CandidateResult(
                        adapter=adapter.name,
                        passed=False,
                        error=f"{type(exc).__name__}: {exc}",
                        output_sha256=None,
                        normalized_output_sha256=None,
                        diff=None,
                    )
                )
        results.append(
            CaseResult(
                id=case.id,
                layer=case.layer,
                source_path=case.source_path,
                input_bytes=len(html_bytes),
                oracle_sha256=sha256_text(oracle_output),
                normalized_oracle_sha256=sha256_text(normalized_oracle),
                results=candidate_results,
                metadata=case.metadata,
            )
        )
    return results


def summarize(results: list[CaseResult]) -> dict[str, object]:
    by_adapter: dict[str, dict[str, int]] = {}
    by_layer: dict[str, dict[str, dict[str, int]]] = {}
    for case in results:
        layer_bucket = by_layer.setdefault(case.layer, {})
        for candidate in case.results:
            adapter_bucket = by_adapter.setdefault(candidate.adapter, {"passed": 0, "failed": 0, "error": 0})
            layer_adapter_bucket = layer_bucket.setdefault(candidate.adapter, {"passed": 0, "failed": 0, "error": 0})
            key = "passed" if candidate.passed else "error" if candidate.error else "failed"
            adapter_bucket[key] += 1
            layer_adapter_bucket[key] += 1
    return {"case_count": len(results), "by_adapter": by_adapter, "by_layer": by_layer}


def write_reports(results: list[CaseResult], report_dir: Path) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {"summary": summarize(results), "cases": [_case_to_dict(case) for case in results]}
    json_path = report_dir / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path = report_dir / "latest.md"
    md_path.write_text(_summary_markdown(payload["summary"], json_path), encoding="utf-8")
    return json_path, md_path


def _case_to_dict(case: CaseResult) -> dict[str, object]:
    data = asdict(case)
    return data


def _summary_markdown(summary: dict[str, object], json_path: Path) -> str:
    lines = ["# Conformance differential report", ""]
    lines.append(f"Full per-fixture JSON: `{json_path}`")
    lines.append("")
    lines.append(f"Case count: `{summary['case_count']}`")
    lines.append("")
    lines.append("## Totals by adapter")
    lines.append("")
    lines.append("| Adapter | Passed | Failed | Errors |")
    lines.append("| --- | ---: | ---: | ---: |")
    for adapter, counts in sorted(summary["by_adapter"].items()):  # type: ignore[index, union-attr]
        lines.append(f"| `{adapter}` | {counts['passed']} | {counts['failed']} | {counts['error']} |")
    lines.append("")
    lines.append("## Totals by layer")
    lines.append("")
    for layer, adapters in sorted(summary["by_layer"].items()):  # type: ignore[index, union-attr]
        lines.append(f"### `{layer}`")
        lines.append("")
        lines.append("| Adapter | Passed | Failed | Errors |")
        lines.append("| --- | ---: | ---: | ---: |")
        for adapter, counts in sorted(adapters.items()):
            lines.append(f"| `{adapter}` | {counts['passed']} | {counts['failed']} | {counts['error']} |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--include-lxml-naive", action="store_true")
    parser.add_argument("--max-diff-chars", type=int, default=4000)
    args = parser.parse_args()

    cases = load_cases(args.fixture_root)
    if args.max_cases is not None:
        cases = cases[: args.max_cases]
    adapters = get_adapters(include_lxml_naive=args.include_lxml_naive)
    results = run_differential(cases, adapters, max_diff_chars=args.max_diff_chars)
    json_path, md_path = write_reports(results, args.report_dir)
    print(json.dumps(summarize(results), indent=2, sort_keys=True))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
