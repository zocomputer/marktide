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
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "tests" / "conformance" / "sources.toml"


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    commit: str
    paths: tuple[str, ...]


def _repo_relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"manifest paths must be repo-relative, got absolute path: {value}")
    return REPO_ROOT / path


def load_manifest(path: Path = MANIFEST_PATH) -> tuple[Path, Path, tuple[Source, ...]]:
    """Read sources.toml as the single source of truth for corpus inputs."""

    manifest = tomllib.loads(path.read_text(encoding="utf-8"))
    corpus = manifest.get("corpus", {})
    fixture_root = _repo_relative_path(_required_str(corpus, "fixture_root", "corpus"))
    lock_path = _repo_relative_path(_required_str(corpus, "lockfile", "corpus"))

    sources: list[Source] = []
    for table_name, table in manifest.get("sources", {}).items():
        context = f"sources.{table_name}"
        fixture_path = _required_str(table, "fixture_path", context)
        fixture_name = Path(fixture_path).name
        if not fixture_name:
            raise ValueError(f"{context}.fixture_path must end in a fixture directory name")
        selected_paths = table.get("selected_paths")
        if not isinstance(selected_paths, list) or not all(isinstance(item, str) for item in selected_paths):
            raise ValueError(f"{context}.selected_paths must be a list of strings")
        sources.append(
            Source(
                name=fixture_name,
                url=_required_str(table, "url", context),
                commit=_required_str(table, "commit", context),
                paths=tuple(selected_paths),
            )
        )
    if not sources:
        raise ValueError("sources.toml must contain at least one [sources.*] table")
    return fixture_root, lock_path, tuple(sources)


def _required_str(table: dict[str, Any], key: str, context: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return value


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


def build_lock(
    destination_root: Path,
    copied_by_source: dict[str, list[str]],
    sources: tuple[Source, ...],
    manifest_path: Path = MANIFEST_PATH,
) -> dict[str, object]:
    lock_sources = {}
    source_by_name = {source.name: source for source in sources}
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
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "sources": lock_sources,
    }


def summarize(destination_root: Path) -> dict[str, object]:
    markdownify_files = sorted((destination_root / "markdownify" / "tests").glob("test_*.py"))
    turndown_index = destination_root / "turndown" / "test" / "index.html"
    commonmark_spec = destination_root / "commonmark-spec" / "spec.txt"

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

    fixture_root, lock_path, sources = load_manifest()
    fixture_root.mkdir(parents=True, exist_ok=True)
    tmp_ctx = tempfile.TemporaryDirectory(prefix="marktide-conformance-")
    tmp = Path(tmp_ctx.name)
    try:
        copied_by_source: dict[str, list[str]] = {}
        for source in sources:
            checkout = clone_at(source, tmp)
            copied_by_source[source.name] = copy_selected_files(source, checkout, fixture_root)

        summary = summarize(fixture_root)
        summary["copied_paths"] = copied_by_source
        summary_path = fixture_root / "_generated_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        lock = build_lock(fixture_root, copied_by_source, sources, MANIFEST_PATH)
        lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        print(json.dumps(summary, indent=2, sort_keys=True))
        print(f"Wrote {summary_path.relative_to(REPO_ROOT)}")
        print(f"Wrote {lock_path.relative_to(REPO_ROOT)}")
    finally:
        if args.keep_temp:
            print(f"Keeping temporary clone directory: {tmp}")
        else:
            tmp_ctx.cleanup()


if __name__ == "__main__":
    main()
