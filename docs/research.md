# HTML→Markdown Research Findings

Date: 2026-06-17  
Bead: `zo-1fp.3`  
Owner: `coder-1-leaf`

## Executive summary

Phase 1 should benchmark our lxml streaming implementation against three Rust-backed Python libraries:

1. **Primary pinned Rust candidate: `html-to-markdown==3.5.7`** (`html_to_markdown`, Rust crate `html-to-markdown-rs`).
   - Why this pin: `3.6.13` is the latest as of 2026-06-17, but it was released on 2026-06-17 and is inside the repo supply-chain cooldown window. `3.5.7` was released on 2026-05-29, installs cleanly, and keeps the same modern `convert()` / `ConversionResult` API shape for benchmarking.
   - Install: `python -m pip install 'html-to-markdown==3.5.7'`.
2. **Comparison Rust candidate: `htmd-py==0.1.2`** (`htmd`, Rust crate `htmd`).
   - Turndown-inspired Rust engine; Python package installs cleanly via a native wheel.
   - Install: `python -m pip install 'htmd-py==0.1.2'`.
3. **Comparison Rust candidate: `html2text_rs==0.2.5`** (`html2text_rs`, Rust `html2text`).
   - Mature Python bindings for HTML→Markdown/plain/rich text. Output is less structurally rich than the top two but useful as a performance and behavior datapoint.
   - Install: `python -m pip install 'html2text_rs==0.2.5'`.

Do **not** treat `fast-html2md==0.2.0` as a primary Rust engine candidate. It installed cleanly, but its PyPI wheel is pure Python and its public API is a BeautifulSoup/tiktoken-oriented wrapper. It may be useful only as an end-user baseline if we want to compare against another LLM-content-extraction package.

## Candidate Rust/Python libraries

### `html-to-markdown` / `html-to-markdown-rs`

- Package: <https://pypi.org/project/html-to-markdown/>
- Repository: <https://github.com/kreuzberg-dev/html-to-markdown>
- Python README: <https://github.com/kreuzberg-dev/html-to-markdown/blob/main/packages/python/README.md>
- Rust crate docs: <https://docs.rs/crate/html-to-markdown-rs/latest/source/README.md>
- Import name: `html_to_markdown`
- Binding/build model: native Python wheels backed by a Rust core. The project describes `html-to-markdown-rs` as the core engine compiled into Python wheels and other language bindings.
- Verified install on local macOS arm64 Python 3.12:
  - `html-to-markdown==3.6.13` installed cleanly as a native `cp310-abi3-macosx_11_0_arm64` wheel.
  - `html-to-markdown==3.5.7` also installed cleanly and is the recommended benchmark pin because it is outside the fresh-release window.
- API smoke test:

```python
from html_to_markdown import convert

result = convert("<h1>Hello</h1><p><b>World</b></p>")
assert result.content == "# Hello\n\n**World**\n"
```

- Notes:
  - `3.6.13` was released 2026-06-17, same day as this research. Keep it out of pinned benchmark requirements unless intentionally testing latest.
  - `3.5.7` was released 2026-05-29 and is old enough for the 7-day supply-chain cooldown.
  - Good primary comparison because it has a maintained multi-language Rust core, typed Python options, metadata extraction, and native wheels.

### `htmd-py` / `htmd`

- Package: <https://pypi.org/project/htmd-py/>
- Python repository: <https://github.com/lmmx/htmd>
- Rust repository: <https://github.com/letmutex/htmd>
- Import name: `htmd`
- Binding/build model: Python bindings for the Rust `htmd` library. The Python project uses native wheels; package metadata and repository describe it as Rust-backed Python bindings.
- Verified install on local macOS arm64 Python 3.12: `htmd-py==0.1.2` installed cleanly as a native `cp312-cp312-macosx_11_0_arm64` wheel.
- API smoke test:

```python
import htmd

markdown = htmd.convert_html("<h1>Hello</h1><p><b>World</b></p>")
assert markdown == "# Hello\n\n**World**"
```

- Notes:
  - The Rust project is Turndown-inspired and claims Turndown test compatibility.
  - Good comparison candidate because its option surface is close to classic HTML→Markdown converters and it is intentionally minimal (`html5ever`-based Rust core).

### `html2text_rs`

- Package metadata: <https://pypi.org/project/html2text-rs/> and <https://pypi.org/project/html2text_rs/> may both resolve depending on normalization.
- Repository: <https://github.com/deedy5/html2text_rs>
- Import name: `html2text_rs`
- Binding/build model: Python binding to the Rust `html2text` crate/library.
- Verified install on local macOS arm64 Python 3.12: `html2text_rs==0.2.5` installed cleanly as a native `cp38-abi3-macosx_11_0_arm64` wheel.
- API smoke test:

```python
import html2text_rs

markdown = html2text_rs.text_markdown("<h1>Hello</h1><p><b>World</b></p>")
assert markdown.startswith("# Hello")
```

- Notes:
  - Output is more text-oriented; in the smoke test bold text was emitted as plain `World`, unlike `html-to-markdown` and `htmd-py`.
  - Include in phase-1 speed and memory benchmarks, but do not use it as the semantic gold standard.

### `fast-html2md`

- Package: <https://pypi.org/project/fast-html2md/>
- Repository: <https://github.com/ancs21/fast-html2md>
- Import name: `fast_html2md`
- Verified install on local macOS arm64 Python 3.12: `fast-html2md==0.2.0` installed cleanly as a `py3-none-any` wheel.
- Caveat: despite the package description referencing a Rust engine, the install artifact is pure Python and pulls `beautifulsoup4` and `tiktoken`. Treat it as a product baseline, not as a core Rust crate with direct bindings.

## Large benchmark fixture files

Generated files live under `benchmarks/fixtures/` and are intentionally gitignored by `.gitignore`:

| File | Target | Actual local size | Generation strategy |
| --- | ---: | ---: | --- |
| `benchmarks/fixtures/small.html` | ~100 KiB | 102,401 bytes | prefix + truncated real-source corpus |
| `benchmarks/fixtures/medium.html` | ~5 MiB | 5,242,881 bytes | repeated real-source corpus |
| `benchmarks/fixtures/large.html` | ~50 MiB | 52,428,801 bytes | repeated real-source corpus |
| `benchmarks/fixtures/xlarge.html` | ~100 MiB | 104,857,601 bytes | repeated real-source corpus |

Source pages used for the deterministic corpus:

- Wikipedia HTML article: <https://en.wikipedia.org/wiki/HTML>
- Wikipedia United States article: <https://en.wikipedia.org/wiki/United_States>
- RFC 9110 HTML: <https://www.rfc-editor.org/rfc/rfc9110.html>
- NASA Apollo chronology table of contents: <https://history.nasa.gov/SP-4029/Apollo_00g_Table_of_Contents.htm>

The NASA page was ~36 MiB locally and gives the corpus a genuinely large real-world HTML document instead of relying only on tiny pages repeated many times.

### Regeneration command

Run from repo root:

```bash
mkdir -p benchmarks/fixtures
python3 - <<'PY'
from pathlib import Path
from urllib.request import Request, urlopen

sources = [
    ("wikipedia_html", "https://en.wikipedia.org/wiki/HTML"),
    ("wikipedia_united_states", "https://en.wikipedia.org/wiki/United_States"),
    ("rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.html"),
    ("nasa_apollo", "https://history.nasa.gov/SP-4029/Apollo_00g_Table_of_Contents.htm"),
]
headers = {"User-Agent": "new-html-parser benchmark fixture generator/0.1"}
chunks = []
for name, url in sources:
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as response:
        data = response.read()
    text = data.decode("utf-8", errors="replace")
    chunks.append(f"\n<!-- source: {name} {url}; bytes={len(data)} -->\n" + text)

base = "\n".join(chunks)
out = Path("benchmarks/fixtures")
out.mkdir(parents=True, exist_ok=True)
targets = {
    "small.html": 100 * 1024,
    "medium.html": 5 * 1024 * 1024,
    "large.html": 50 * 1024 * 1024,
    "xlarge.html": 100 * 1024 * 1024,
}
for filename, target_bytes in targets.items():
    prefix = (
        "<!doctype html>\n"
        f"<html><head><meta charset='utf-8'><title>{filename}</title></head><body>\n"
        f"<!-- generated target_bytes={target_bytes}; repeat source corpus deterministically -->\n"
    )
    suffix = "\n</body></html>\n"
    body_bytes = target_bytes - len(prefix.encode()) - len(suffix.encode())
    reps = max(1, body_bytes // len(base.encode()) + 1)
    raw = (prefix + (base * reps) + suffix).encode("utf-8")[:target_bytes]
    if not raw.endswith(b"\n"):
        raw += b"\n"
    (out / filename).write_bytes(raw)
    print(filename, (out / filename).stat().st_size)
PY
ls -lh benchmarks/fixtures
```

Expected local output from the 2026-06-17 run:

```text
small.html   100K
medium.html  5.0M
large.html    50M
xlarge.html  100M
```

## Phase-2 conformance corpus options

There is no single standards-body HTML→Markdown conformance suite. HTML→Markdown is an inverse conversion with many valid Markdown outputs for the same HTML. Use a layered corpus instead.

### Layer 1: `python-markdownify` tests as compatibility baseline

- Repository: <https://github.com/matthewwithanm/python-markdownify>
- Pull command:

```bash
git clone --depth 1 https://github.com/matthewwithanm/python-markdownify.git /tmp/python-markdownify
find /tmp/python-markdownify -maxdepth 3 -type f \( -name '*test*.py' -o -name '*tests*' \)
```

- Suggested use:
  - Import or translate individual test vectors into `tests/conformance/markdownify_cases/`.
  - Mark exact-output tests as `compat_markdownify` because our desired output may intentionally differ in whitespace, wrapping, or unsupported tags.
  - Strongest value: preserving compatibility for cases users already expect from `markdownify`, the library being replaced.

### Layer 2: Turndown tests and `turndown-attendant` HTML-case format

- Turndown repository: <https://github.com/mixmark-io/turndown>
- Turndown attendant repository: <https://github.com/mixmark-io/turndown-attendant>
- Pull command:

```bash
git clone --depth 1 https://github.com/mixmark-io/turndown.git /tmp/turndown
git clone --depth 1 https://github.com/mixmark-io/turndown-attendant.git /tmp/turndown-attendant
find /tmp/turndown -maxdepth 4 -type f \( -name '*test*' -o -name '*.html' \)
find /tmp/turndown-attendant -maxdepth 4 -type f
```

- Corpus format:
  - `turndown-attendant` documents the convenient HTML fixture format: each case is a `<div class="case" data-name="...">` with nested `<div class="input">` and `<pre class="expected">` nodes.
- Suggested use:
  - Put normalized converted cases under `tests/conformance/turndown_cases/`.
  - Use exact output for simple inline/block/list/table cases.
  - Use semantic rendered-HTML comparison for cases where whitespace and Markdown style choices differ.

### Layer 3: Pandoc as an oracle and edge-case corpus

- Repository: <https://github.com/jgm/pandoc>
- Manual: <https://pandoc.org/MANUAL.html>
- Pull command:

```bash
git clone --depth 1 https://github.com/jgm/pandoc.git /tmp/pandoc
find /tmp/pandoc -maxdepth 4 -type f \( -iname '*html*' -o -path '*/test/*' -o -path '*/tests/*' \)
```

- Suggested use:
  - Do not blindly assert our output equals Pandoc output; Pandoc has a rich document model and distinct Markdown dialect choices.
  - Use Pandoc for oracle comparisons on hard HTML structures: nested lists, tables, code/pre blocks, entities, inline formatting boundaries, malformed HTML, and block/inline transitions.
  - Recommended check: render both our Markdown and Pandoc's Markdown back to normalized HTML, then compare normalized DOM/text for semantic equivalence.

### Layer 4: CommonMark emitted-Markdown validation, not HTML→Markdown conformance

- Repository: <https://github.com/commonmark/commonmark-spec>
- Spec site: <https://spec.commonmark.org/>
- Pull command:

```bash
git clone --depth 1 https://github.com/commonmark/commonmark-spec.git /tmp/commonmark-spec
```

- Suggested use:
  - CommonMark tests are Markdown→HTML tests, so they are not direct HTML→Markdown fixtures.
  - Use the CommonMark parser/spec to validate that emitted Markdown is parseable and stable under Markdown→HTML normalization.
  - Good property test: for each HTML fixture, convert HTML→Markdown, render Markdown→HTML with a CommonMark parser, normalize the DOM, and assert important text/link/table/code invariants.

## Recommended phase-1 benchmark matrix

Benchmark each converter on all four fixture sizes with the same runner process isolation:

| Converter | Package pin | API call | Role |
| --- | --- | --- | --- |
| New library | local source | planned streaming API | system under test |
| `markdownify` | existing dev dependency | `markdownify.markdownify(html)` | incumbent baseline |
| `html-to-markdown` | `3.5.7` | `html_to_markdown.convert(html).content` | primary Rust baseline |
| `htmd-py` | `0.1.2` | `htmd.convert_html(html)` | Turndown-inspired Rust baseline |
| `html2text_rs` | `0.2.5` | `html2text_rs.text_markdown(html)` | text-oriented Rust baseline |
| `fast-html2md` | `0.2.0`, optional | `fast_html2md.HTMLToMarkdown(...).convert(...)` after API inspection | product wrapper baseline only |

Measurements to record:

- Wall-clock time.
- Peak RSS.
- Input bytes / output bytes.
- Whether conversion is whole-document-only or can stream/chunk.
- Whether conversion preserves key structures on a small semantic sample: headings, nested lists, tables, links, images, `pre`/`code`, entities, and malformed tags.

## Open follow-ups

- Before adding any package to `pyproject.toml`, re-check upload dates and pin versions outside the supply-chain cooldown unless there is an explicit exception.
- Convert this research into checked-in benchmark/conformance harness code in the implementation beads; `benchmarks/fixtures/*.html` should remain generated and gitignored.
- When phase-2 conformance starts, snapshot external corpus commit SHAs in a manifest so CI is reproducible.
