"""Verify the committed canonical example across supported converters.

Run from the repository root with:

    make verify-canonical

The check compares rendered Markdown semantics, not Markdown bytes: different
libraries choose different heading/list/fence spellings for equivalent Markdown.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "tests" / "conformance") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tests" / "conformance"))

from benchmarks.harness.adapters.marktide_adapter import Html2MdAdapter  # noqa: E402
from benchmarks.harness.adapters.html_to_markdown_adapter import HtmlToMarkdownAdapter  # noqa: E402
from benchmarks.harness.adapters.markdownify_adapter import MarkdownifyAdapter  # noqa: E402
from differential import _canonical_html_fragment  # noqa: E402

CANONICAL_HTML = REPO_ROOT / "examples" / "canonical.html"
CANONICAL_MD = REPO_ROOT / "examples" / "canonical.md"


@dataclass(frozen=True)
class Conversion:
    name: str
    markdown: str
    required: bool = True


def _render_markdown(markdown: str) -> str:
    from markdown_it import MarkdownIt

    return MarkdownIt("commonmark").render(markdown)


def _semantic_key(markdown: str) -> object:
    return _canonical_html_fragment(_render_markdown(markdown))


def _pandoc_markdown(html: bytes) -> str | None:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        return None
    result = subprocess.run(
        [pandoc, "--from=html", "--to=gfm"],
        input=html,
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def main() -> int:
    html = CANONICAL_HTML.read_bytes()
    expected_markdown = CANONICAL_MD.read_text(encoding="utf-8")
    ours = Html2MdAdapter().convert(html)
    if expected_markdown.rstrip("\n") != ours.rstrip("\n"):
        print("ERROR: examples/canonical.md is stale; regenerate it from examples/canonical.html", file=sys.stderr)
        print("expected file:", repr(expected_markdown), file=sys.stderr)
        print("live output:", repr(ours), file=sys.stderr)
        return 1

    conversions = [
        Conversion("marktide", ours),
        Conversion("markdownify", MarkdownifyAdapter().convert(html)),
        Conversion("html_to_markdown (Rust)", HtmlToMarkdownAdapter().convert(html)),
    ]
    pandoc_markdown = _pandoc_markdown(html)
    if pandoc_markdown is None:
        print("pandoc: SKIP (pandoc executable not installed; install pandoc to include it in this check)")
    else:
        conversions.append(Conversion("pandoc", pandoc_markdown))

    baseline = _semantic_key(ours)
    failed = False
    print("Canonical example functional-equivalence check")
    print("================================================")
    print(f"input:  {CANONICAL_HTML.relative_to(REPO_ROOT)}")
    print(f"output: {CANONICAL_MD.relative_to(REPO_ROOT)}")
    print("comparison: Markdown bytes may differ; rendered HTML is normalized and compared")
    print()
    for conversion in conversions:
        equivalent = _semantic_key(conversion.markdown) == baseline
        status = "PASS" if equivalent else "FAIL"
        print(f"{conversion.name:24} {status}")
        if not equivalent and conversion.required:
            failed = True
    if failed:
        print("ERROR: at least one required converter is not functionally equivalent", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
