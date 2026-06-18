#!/usr/bin/env python3
"""Regenerate large benchmark HTML fixtures and a committed hash lockfile.

The fixture HTML files are intentionally gitignored because they are large.
This script downloads real source pages, assembles valid outer HTML documents
without raw byte truncation, and writes benchmarks/fixtures.lock.json with
source and fixture SHA-256 hashes for verification.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "benchmarks" / "fixtures"
LOCK_PATH = REPO_ROOT / "benchmarks" / "fixtures.lock.json"
USER_AGENT = "new-html-parser benchmark fixture generator/0.2"

SOURCES = [
    ("wikipedia_html", "https://en.wikipedia.org/wiki/HTML"),
    ("wikipedia_united_states", "https://en.wikipedia.org/wiki/United_States"),
    ("rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.html"),
    ("nasa_apollo", "https://history.nasa.gov/SP-4029/Apollo_00g_Table_of_Contents.htm"),
]

TARGETS = {
    "small.html": 100 * 1024,
    "medium.html": 5 * 1024 * 1024,
    "large.html": 50 * 1024 * 1024,
    "xlarge.html": 100 * 1024 * 1024,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_sources() -> list[dict[str, str | int]]:
    fetched = []
    for name, url in SOURCES:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=60) as response:
            raw = response.read()
        fetched.append(
            {
                "name": name,
                "url": url,
                "bytes": len(raw),
                "sha256": sha256_bytes(raw),
                "text": raw.decode("utf-8", errors="replace"),
            }
        )
    return fetched


def text_words(sources: list[dict[str, str | int]]) -> str:
    combined = "\n".join(str(source["text"]) for source in sources)
    stripped = re.sub(r"<[^>]+>", " ", combined)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped or "html markdown benchmark fixture text"


def build_fixture(filename: str, target_bytes: int, sources: list[dict[str, str | int]], words: str) -> bytes:
    head = (
        "<!doctype html>\n"
        "<html><head><meta charset='utf-8'>"
        f"<title>{html.escape(filename)}</title></head><body>\n"
        f"<!-- generated target_bytes={target_bytes}; no raw byte truncation; source_count={len(sources)} -->\n"
    )
    tail = "</body></html>\n"
    parts = [head]

    # Include complete real HTML documents as raw nested sections only when doing
    # so keeps the fixture close to the requested size. We never slice a source
    # document at an arbitrary byte offset; smaller fixtures use synthetic HTML
    # paragraphs/lists/code built from real page text instead.
    source_sections = []
    for source in sources:
        section = (
            f"<section data-source='{html.escape(str(source['name']))}'>\n"
            f"<h1>Source {html.escape(str(source['name']))}</h1>\n"
            f"{str(source['text'])}\n"
            "</section>\n"
        )
        source_sections.append((len(section.encode("utf-8")), section))
    source_sections.sort(key=lambda item: item[0])

    added = True
    while added:
        added = False
        current_size = len(("".join(parts) + tail).encode("utf-8"))
        for section_size, section in source_sections:
            if current_size + section_size + len(tail.encode("utf-8")) <= target_bytes * 1.10:
                parts.append(section)
                added = True
                break

    filler_seed = html.escape(words)
    cursor = 0
    paragraph_id = 0
    while len(("".join(parts) + tail).encode("utf-8")) < target_bytes:
        remaining = target_bytes - len(("".join(parts) + tail).encode("utf-8"))
        if remaining < 64:
            break
        take = max(16, min(len(filler_seed), remaining - 64, 4096))
        snippet = filler_seed[cursor : cursor + take]
        if len(snippet) < take:
            cursor = 0
            snippet = filler_seed[:take]
        cursor += take
        parts.append(
            f"<article data-filler='{paragraph_id}'>"
            f"<h2>Filler {paragraph_id}</h2>"
            f"<p>{snippet}</p>"
            f"<ul><li>{snippet[:80]}</li><li><a href='https://example.com/{paragraph_id}'>link {paragraph_id}</a></li></ul>"
            f"<pre><code>{snippet[:160]}</code></pre>"
            "</article>\n"
        )
        paragraph_id += 1

    data = ("".join(parts) + tail).encode("utf-8")
    # Do not truncate; being slightly over the target is intentional so the
    # document remains syntactically closed and parseable.
    return data


def assert_parseable(data: bytes, filename: str) -> None:
    text = data.decode("utf-8")
    if not text.endswith("</body></html>\n"):
        raise AssertionError(f"{filename}: fixture does not end with closing body/html tags")
    try:
        from lxml import html as lxml_html  # type: ignore
    except Exception:
        return
    lxml_html.fromstring(data)


def main() -> None:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    sources = fetch_sources()
    words = text_words(sources)
    fixtures = []
    for filename, target_bytes in TARGETS.items():
        data = build_fixture(filename, target_bytes, sources, words)
        assert_parseable(data, filename)
        path = FIXTURE_ROOT / filename
        path.write_bytes(data)
        fixtures.append(
            {
                "path": str(path.relative_to(REPO_ROOT)),
                "target_bytes": target_bytes,
                "actual_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "parse_guard": "closed outer HTML and lxml.html parse succeeded when lxml was importable",
            }
        )
        print(f"{filename}: {path.stat().st_size} bytes")

    lock = {
        "version": 1,
        "generated_by": str(Path(__file__).resolve().relative_to(REPO_ROOT)),
        "no_raw_byte_truncation": True,
        "sources": [
            {k: v for k, v in source.items() if k != "text"}
            for source in sources
        ],
        "fixtures": fixtures,
    }
    LOCK_PATH.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {LOCK_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
