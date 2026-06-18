#!/usr/bin/env python3
"""Regenerate gitignored HTML→Markdown phase-2 conformance fixtures.

The committed manifest at tests/conformance/sources.toml records source URLs,
commits, selected paths, and normalization policy. This script materializes the
raw fixture files under tests/conformance/fixtures/, which is intentionally
ignored by git because the data is external-source test corpus material.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "conformance" / "fixtures"
LOCK_PATH = REPO_ROOT / "tests" / "conformance" / "fixtures.lock.json"


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    commit: str
    paths: tuple[str, ...]


SOURCES: tuple[Source, ...] = (
    Source(
        name="markdownify",
        url="https://github.com/matthewwithanm/python-markdownify.git",
        commit="add391a6235cbc66af30ec0202cb00cb0ff0eb4c",
        paths=(
            "tests/__init__.py",
            "tests/test_advanced.py",
            "tests/test_args.py",
            "tests/test_basic.py",
            "tests/test_conversions.py",
            "tests/test_custom_converter.py",
            "tests/test_escaping.py",
            "tests/test_lists.py",
            "tests/test_tables.py",
            "tests/types.py",
            "tests/utils.py",
            "README.rst",
            "LICENSE",
        ),
    ),
    Source(
        name="turndown",
        url="https://github.com/mixmark-io/turndown.git",
        commit="fb7a865ef5eba4081dfd4e20a894a61ef7a2edca",
        paths=(
            "test/index.html",
            "test/turndown-test.js",
            "test/internals-test.js",
            "package.json",
            "LICENSE",
        ),
    ),
    Source(
        name="turndown-attendant",
        url="https://github.com/mixmark-io/turndown-attendant.git",
        commit="651033cae3862b2fadea2f778ab7902ca5f3eee8",
        paths=(
            "README.md",
            "attendant.js",
            "package.json",
            "LICENSE",
        ),
    ),
    Source(
        name="pandoc",
        url="https://github.com/jgm/pandoc.git",
        commit="850c7b9613aa7beb1aed8c2c1f7abb01eaf3023e",
        paths=(
            "test/Tests/Readers/HTML.hs",
            "test/Tests/Writers/HTML.hs",
            "test/html-reader.html",
            "test/lhs-test.html",
            "test/s5-basic.html",
            "test/s5-fancy.html",
            "test/s5-fragment.html",
            "test/s5-inserts.html",
            "test/fb2/images-embedded.html",
            "test/ipynb/rank.out.html",
            "data/templates/default.html4",
            "data/templates/default.html5",
            "COPYING.md",
        ),
    ),
    Source(
        name="commonmark-spec",
        url="https://github.com/commonmark/commonmark-spec.git",
        commit="3da939428d80f146f270cd1765e4ba462e96bb1b",
        paths=(
            "spec.txt",
            "test/spec_tests.py",
            "test/normalize.py",
            "LICENSE",
        ),
    ),
)


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def clone_at(source: Source, checkout_root: Path) -> Path:
    checkout = checkout_root / source.name
    run(["git", "clone", "--no-checkout", "--depth", "1", source.url, str(checkout)])
    run(["git", "fetch", "--depth", "1", "origin", source.commit], cwd=checkout)
    run(["git", "checkout", "--detach", source.commit], cwd=checkout)
    return checkout


def copy_selected_files(source: Source, checkout: Path, destination_root: Path) -> list[str]:
    copied: list[str] = []
    target_base = destination_root / source.name
    if target_base.exists():
        shutil.rmtree(target_base)
    for rel in source.paths:
        src = checkout / rel
        if not src.exists():
            raise FileNotFoundError(f"{source.name}: selected path missing: {rel}")
        dst = target_base / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    return copied


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_lock(destination_root: Path, copied_by_source: dict[str, list[str]]) -> dict[str, object]:
    lock_sources = {}
    source_by_name = {source.name: source for source in SOURCES}
    for name, copied_paths in copied_by_source.items():
        source = source_by_name[name]
        files = []
        for rel in copied_paths:
            path = destination_root / name / rel
            files.append({
                "path": f"{name}/{rel}",
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
        lock_sources[name] = {
            "url": source.url,
            "commit": source.commit,
            "files": files,
        }
    return {
        "version": 1,
        "fixture_root": str(destination_root.relative_to(REPO_ROOT)),
        "generated_by": str(Path(__file__).resolve().relative_to(REPO_ROOT)),
        "sources": lock_sources,
    }


def summarize(destination_root: Path) -> dict[str, object]:
    markdownify_files = sorted((destination_root / "markdownify" / "tests").glob("test_*.py"))
    turndown_index = destination_root / "turndown" / "test" / "index.html"
    commonmark_spec = destination_root / "commonmark-spec" / "spec.txt"
    pandoc_root = destination_root / "pandoc" / "test"

    return {
        "fixture_root": str(destination_root.relative_to(REPO_ROOT)),
        "sources": {
            "markdownify": {
                "test_py_files": len(markdownify_files),
                "assertion_count_approx": sum(
                    path.read_text(encoding="utf-8").count("assert ") for path in markdownify_files
                ),
            },
            "turndown": {
                "attendant_case_count": len(
                    re.findall(r'class=["\\\']case["\\\']', turndown_index.read_text(encoding="utf-8"))
                ),
            },
            "pandoc": {
                "html_files": len(list(pandoc_root.rglob("*.html"))),
                "reader_haskell_specs": 1,
                "writer_haskell_specs": 1,
            },
            "commonmark-spec": {
                "spec_examples": len(
                    re.findall(r"^`{32} example$", commonmark_spec.read_text(encoding="utf-8"), re.M)
                ),
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-temp", action="store_true", help="do not delete temporary clone directory")
    args = parser.parse_args()

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    tmp_ctx = tempfile.TemporaryDirectory(prefix="html2md-conformance-")
    tmp = Path(tmp_ctx.name)
    try:
        copied_by_source: dict[str, list[str]] = {}
        for source in SOURCES:
            checkout = clone_at(source, tmp)
            copied_by_source[source.name] = copy_selected_files(source, checkout, FIXTURE_ROOT)

        summary = summarize(FIXTURE_ROOT)
        summary["copied_paths"] = copied_by_source
        summary_path = FIXTURE_ROOT / "_generated_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        lock = build_lock(FIXTURE_ROOT, copied_by_source)
        LOCK_PATH.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        print(json.dumps(summary, indent=2, sort_keys=True))
        print(f"Wrote {summary_path.relative_to(REPO_ROOT)}")
        print(f"Wrote {LOCK_PATH.relative_to(REPO_ROOT)}")
    finally:
        if args.keep_temp:
            print(f"Keeping temporary clone directory: {tmp}")
        else:
            tmp_ctx.cleanup()


if __name__ == "__main__":
    main()
