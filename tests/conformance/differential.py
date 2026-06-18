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
from typing import Any, Iterable, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import lxml.etree as etree  # noqa: E402  # ty: ignore[unresolved-import]
import lxml.html as lxml_html  # noqa: E402

from benchmarks.harness.adapters.base import Adapter, OptionMap, get_adapters  # noqa: E402
from marktide.options import markdownify_compat  # noqa: E402

DEFAULT_FIXTURE_ROOT = REPO_ROOT / "tests" / "conformance" / "fixtures"
DEFAULT_REPORT_DIR = REPO_ROOT / "tests" / "conformance" / "reports"
PRIMARY_MARKDOWNIFY_LAYERS = frozenset({"golden", "markdownify_tests"})


@dataclass(frozen=True)
class Html2mdAdapter:
    """Local correctness adapter for the in-repo marktide converter.

    Kept in tests/conformance so the shared benchmark adapter interface remains
    owned by coder-3 while phase-2 correctness wiring can start immediately.
    """

    name: str = "marktide"
    package: str = "marktide local"
    engine: str = "lxml target parser + Python emitter"
    option_map: OptionMap = field(default_factory=OptionMap)

    def convert(self, html_bytes: bytes) -> str:
        import marktide

        return marktide.convert(html_bytes)


def _marktide_is_available() -> bool:
    try:
        import marktide  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


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


def normalize_input_html(case: Case) -> str:
    """Apply corpus-specific source normalization before oracle conversion.

    The primary markdownify-oracle layers intentionally pass through unchanged.
    Secondary corpora can contain fixture chrome that is useful for smoke
    coverage but should not dominate fidelity accounting.
    """

    if case.layer != "pandoc":
        return case.html
    return strip_pandoc_chrome(case.html)


def strip_pandoc_chrome(html: str) -> str:
    """Return body content with Pandoc template/presentation chrome removed."""

    try:
        document = lxml_html.fromstring(html)
    except (ValueError, etree.ParserError):
        return html
    for element in document.xpath("//head|//style|//script|//meta|//link|//title"):
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)
    bodies = document.xpath("//body")
    root = bodies[0] if bodies else document
    return _inner_html(root)


def commonmark_semantic_equal(expected_markdown: str, actual_markdown: str) -> bool:
    """Compare CommonMark-rendered HTML trees instead of Markdown strings."""

    try:
        from markdown_it import MarkdownIt
    except ModuleNotFoundError:
        return False
    renderer = MarkdownIt("commonmark")
    expected_html = renderer.render(expected_markdown)
    actual_html = renderer.render(actual_markdown)
    return _canonical_html_fragment(expected_html) == _canonical_html_fragment(actual_html)


def _canonical_html_fragment(html: str) -> object:
    parser = lxml_html.HTMLParser(remove_comments=True)
    root = lxml_html.fragment_fromstring(html, create_parent="div", parser=parser)
    return _canonical_html_node(root, preserve_text=False)


def _canonical_html_node(element, *, preserve_text: bool) -> tuple[object, ...]:
    tag = str(element.tag).lower()
    child_preserve = preserve_text or tag in {"pre", "code"}
    attrs = tuple(sorted((str(key).lower(), str(value)) for key, value in element.attrib.items()))
    text = _canonical_html_text(element.text or "", preserve=child_preserve)
    children = tuple(_canonical_html_node(child, preserve_text=child_preserve) for child in element)
    tail = _canonical_html_text(element.tail or "", preserve=preserve_text)
    return tag, attrs, text, children, tail


def _canonical_html_text(text: str, *, preserve: bool) -> str:
    if preserve:
        return text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", text).strip()


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
        data_options = case_el.get("data-options")
        cases.append(
            Case(
                id=f"turndown:{index:04d}:{_slug(name)}",
                layer="turndown_options" if data_options else "turndown",
                source_path=_display_path(path),
                html=_inner_html(input_nodes[0]),
                upstream_expected_markdown=expected_nodes[0].text if expected_nodes else None,
                metadata={"name": name, "data_options": data_options},
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
        if path.name == "test_custom_converter.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue
            extracted = _extract_md_assert(node.test)
            if extracted is None:
                continue
            html_input, expected, md_kwargs = extracted
            line = getattr(node, "lineno", 0)
            cases.append(
                Case(
                    id=f"markdownify:{path.stem}:{line}",
                    layer="markdownify_tests",
                    source_path=_display_path(path),
                    html=html_input,
                    upstream_expected_markdown=expected,
                    metadata={"line": line, "markdownify_options": {"strip_document": None, **md_kwargs}},
                )
            )
    return cases


_MARKDOWNIFY_NAME_CONSTANTS = {
    "ATX": "atx",
    "ATX_CLOSED": "atx_closed",
    "UNDERLINED": "underlined",
    "BACKSLASH": "backslash",
    "SPACES": "spaces",
    "ASTERISK": "*",
    "UNDERSCORE": "_",
    "STRIP": "strip",
    "LSTRIP": "lstrip",
    "RSTRIP": "rstrip",
}


def _extract_md_assert(expr: ast.expr) -> tuple[str, str, dict[str, object]] | None:
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
    kwargs: dict[str, object] = {}
    for keyword in left.keywords:
        if keyword.arg is None:
            return None
        value = _literal_md_kwarg(keyword.value)
        if value is _UNSUPPORTED_KWARG:
            return None
        kwargs[keyword.arg] = value
    return left.args[0].value, right.value, kwargs


_UNSUPPORTED_KWARG = object()


def _literal_md_kwarg(node: ast.expr) -> object:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return _MARKDOWNIFY_NAME_CONSTANTS.get(node.id, _UNSUPPORTED_KWARG)
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_literal_md_kwarg(elt) for elt in node.elts]
        if any(value is _UNSUPPORTED_KWARG for value in values):
            return _UNSUPPORTED_KWARG
        return values
    return _UNSUPPORTED_KWARG


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
        normalized_html = normalize_input_html(case)
        html_bytes = normalized_html.encode("utf-8", errors="replace")
        oracle_output = _oracle_output(case, oracle, html_bytes)
        normalized_oracle = normalize_markdown(oracle_output)
        candidate_results: list[CandidateResult] = []
        for adapter in candidates:
            try:
                output = _candidate_output(case, adapter, html_bytes)
                normalized = normalize_markdown(output)
                passed = (
                    commonmark_semantic_equal(normalized_oracle, normalized)
                    if case.layer == "commonmark_expected_html"
                    else normalized == normalized_oracle
                )
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


def _oracle_output(case: Case, oracle: Adapter, html_bytes: bytes) -> str:
    if case.layer == "markdownify_tests" and case.upstream_expected_markdown is not None:
        return case.upstream_expected_markdown
    return oracle.convert(html_bytes)


def _candidate_output(case: Case, adapter: Adapter, html_bytes: bytes) -> str:
    if case.layer == "markdownify_tests" and adapter.name in {"marktide", "marktide_streaming"}:
        import marktide

        raw_options = case.metadata.get("markdownify_options", {})
        md_options = cast(dict[str, Any], raw_options if isinstance(raw_options, dict) else {})
        options = markdownify_compat(**md_options)
        if adapter.name == "marktide_streaming":
            return "".join(marktide.convert_stream([html_bytes], options=options))
        return marktide.convert(html_bytes, options=options)
    return adapter.convert(html_bytes)


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
    return {
        "case_count": len(results),
        "primary_markdownify_layers": sorted(PRIMARY_MARKDOWNIFY_LAYERS),
        "primary_markdownify_oracle": _summarize_primary_markdownify(results),
        "by_adapter": by_adapter,
        "by_layer": by_layer,
    }


def _summarize_primary_markdownify(results: list[CaseResult]) -> dict[str, dict[str, int]]:
    primary: dict[str, dict[str, int]] = {}
    for case in results:
        if case.layer not in PRIMARY_MARKDOWNIFY_LAYERS:
            continue
        for candidate in case.results:
            adapter_bucket = primary.setdefault(candidate.adapter, {"passed": 0, "failed": 0, "error": 0})
            key = "passed" if candidate.passed else "error" if candidate.error else "failed"
            adapter_bucket[key] += 1
    return primary


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
    primary_layers = cast(list[str], summary["primary_markdownify_layers"])
    primary_counts = cast(dict[str, dict[str, int]], summary["primary_markdownify_oracle"])
    by_adapter = cast(dict[str, dict[str, int]], summary["by_adapter"])
    by_layer = cast(dict[str, dict[str, dict[str, int]]], summary["by_layer"])
    lines = ["# Conformance differential report", ""]
    lines.append(f"Full per-fixture JSON: `{json_path}`")
    lines.append("")
    lines.append(f"Case count: `{summary['case_count']}`")
    lines.append("")
    lines.append("## Primary markdownify-oracle fidelity")
    lines.append("")
    layers = ", ".join(f"`{layer}`" for layer in primary_layers)
    lines.append(f"Primary layers: {layers}")
    lines.append("")
    lines.append("| Adapter | Passed | Failed | Errors | Fidelity |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for adapter, counts in sorted(primary_counts.items()):
        total = counts["passed"] + counts["failed"] + counts["error"]
        fidelity = (counts["passed"] / total * 100) if total else 0.0
        lines.append(
            f"| `{adapter}` | {counts['passed']} | {counts['failed']} | {counts['error']} | {fidelity:.1f}% |"
        )
    lines.append("")
    lines.append("## Totals by adapter")
    lines.append("")
    lines.append("| Adapter | Passed | Failed | Errors |")
    lines.append("| --- | ---: | ---: | ---: |")
    for adapter, counts in sorted(by_adapter.items()):
        lines.append(f"| `{adapter}` | {counts['passed']} | {counts['failed']} | {counts['error']} |")
    lines.append("")
    lines.append("## Totals by layer")
    lines.append("")
    for layer, adapters in sorted(by_layer.items()):
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
    if _marktide_is_available() and all(adapter.name != "marktide" for adapter in adapters):
        adapters.append(Html2mdAdapter())
    results = run_differential(cases, adapters, max_diff_chars=args.max_diff_chars)
    json_path, md_path = write_reports(results, args.report_dir)
    print(json.dumps(summarize(results), indent=2, sort_keys=True))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
