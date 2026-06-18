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


## Candidate metadata: license, maintenance, wheel coverage

| Candidate | License metadata | Maintenance signal checked 2026-06-17 | Wheel/platform coverage checked 2026-06-17 | Supply-chain note |
| --- | --- | --- | --- | --- |
| `html-to-markdown==3.5.7` | PyPI license expression: MIT. | Active: latest PyPI release line was `3.6.13` on 2026-06-17; pinned `3.5.7` was released 2026-05-29. | Native `cp310-abi3` wheels for macOS x86_64/arm64, manylinux2014 x86_64/aarch64, Windows amd64, plus sdist. | Use `3.5.7` for benchmark pins because `3.6.13` is inside the 7-day cooldown. |
| `htmd-py==0.1.2` | PyPI classifier: Apache Software License. | Active enough: releases in 2025 and 2026; `0.1.2` uploaded 2026-04-15. | Broad native wheels across CPython 3.9-3.13, macOS x86_64/arm64, manylinux/musllinux architectures, and Windows amd64. | Outside cooldown. |
| `html2text_rs==0.2.5` | PyPI metadata: MIT License. | Moderate: multiple releases from 2024-2025; `0.2.5` uploaded 2025-08-30. | `cp38-abi3` and `cp313` wheels for macOS x86_64/arm64, manylinux/musllinux architectures, Windows amd64/win32, plus sdist. | Outside cooldown. |
| `fast-html2md==0.2.0` | PyPI license expression/classifier: MIT. | Low-to-moderate: sparse release history; `0.2.0` uploaded 2026-06-06. | Pure Python `py3-none-any` wheel plus sdist; pulls `beautifulsoup4` and `tiktoken`. | Outside cooldown but not a primary Rust engine candidate. |

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

Generated files live under `benchmarks/fixtures/` and are intentionally gitignored by `.gitignore`. Their committed verification lockfile is `benchmarks/fixtures.lock.json`, and the reproducible generator is `scripts/regenerate_benchmark_fixtures.py`. The generator does **not** truncate raw HTML bytes; every fixture is closed with `</body></html>` and is parsed with `lxml.html` when `lxml` is importable:

| File | Target | Actual local size | Generation strategy |
| --- | ---: | ---: | --- |
| `benchmarks/fixtures/small.html` | ~100 KiB | 102,740 bytes | parse-guarded generated HTML from real page text |
| `benchmarks/fixtures/medium.html` | ~5 MiB | 5,606,346 bytes | complete real HTML source sections plus generated filler |
| `benchmarks/fixtures/large.html` | ~50 MiB | 57,590,748 bytes | complete real HTML source sections plus generated filler |
| `benchmarks/fixtures/xlarge.html` | ~100 MiB | 115,181,313 bytes | complete real HTML source sections plus generated filler |

Source pages used for the deterministic corpus:

- Wikipedia HTML article: <https://en.wikipedia.org/wiki/HTML>
- Wikipedia United States article: <https://en.wikipedia.org/wiki/United_States>
- RFC 9110 HTML: <https://www.rfc-editor.org/rfc/rfc9110.html>
- NASA Apollo chronology table of contents: <https://history.nasa.gov/SP-4029/Apollo_00g_Table_of_Contents.htm>

The NASA page was ~36 MiB locally and gives the corpus a genuinely large real-world HTML document instead of relying only on tiny pages repeated many times.

### Regeneration command

Run from repo root:

```bash
python3 scripts/regenerate_benchmark_fixtures.py
```

The script writes:

- `benchmarks/fixtures/small.html`
- `benchmarks/fixtures/medium.html`
- `benchmarks/fixtures/large.html`
- `benchmarks/fixtures/xlarge.html`
- `benchmarks/fixtures.lock.json`

The committed lockfile records the source URL byte hashes and fixture byte hashes. The 2026-06-17 fixture hashes are:

| File | SHA-256 |
| --- | --- |
| `benchmarks/fixtures/small.html` | `0ee1ec952ec5279b84f18f44c43d6d2c100bb159aa62c399b48f0b611b4bdbf3` |
| `benchmarks/fixtures/medium.html` | `c917eb770d068cb35a2f8c463fbc8014ae66e7d7416b05059e33ebfa89956afb` |
| `benchmarks/fixtures/large.html` | `7c9ae8a809b111b779433177ee8695c0bb154f7e9749fda94ba7598314bf16a6` |
| `benchmarks/fixtures/xlarge.html` | `a0704f7f1aefa8fee72f690c509c1fd6df4538a216bdab83deb4dfceda4bdb27` |

## Phase-2 conformance corpus options

There is no single standards-body HTML→Markdown conformance suite. HTML→Markdown is an inverse conversion with many valid Markdown outputs for the same HTML. Use the staged layered corpus under `tests/conformance/`.

Committed corpus control files:

- `tests/conformance/sources.toml` — source URLs, exact commit SHAs, licenses, selected source paths, fixture roles, case formats, expected-output normalization policy, and local case counts.
- `tests/conformance/fixtures.lock.json` — generated fixture byte counts and SHA-256 hashes for byte-for-byte reproducibility.
- `scripts/regenerate_conformance_corpus.py` — scripted import transform. It clones each source at the pinned commit, copies only selected files into `tests/conformance/fixtures/`, and rewrites `tests/conformance/fixtures.lock.json`.

Generated corpus files live under `tests/conformance/fixtures/` and are intentionally gitignored. Regenerate from repo root:

```bash
python3 scripts/regenerate_conformance_corpus.py
```

### Layer 1: `python-markdownify` tests as compatibility baseline

- Repository: <https://github.com/matthewwithanm/python-markdownify>
- Pinned commit: `add391a6235cbc66af30ec0202cb00cb0ff0eb4c`
- License: MIT
- Generated fixture path: `tests/conformance/fixtures/markdownify/`
- Selected source paths: `tests/test_*.py`, `tests/types.py`, `tests/utils.py`, `README.rst`, `LICENSE`.
- Local staged count: 8 `test_*.py` files, approximately 323 inline `assert` statements.
- Expected-output policy: exact-output compatibility baseline unless a future harness marks a case semantic-only.

Strongest value: preserving compatibility for cases users already expect from `markdownify`, the library being replaced.

### Layer 2: Turndown tests and `turndown-attendant` HTML-case format

- Turndown repository: <https://github.com/mixmark-io/turndown>
- Turndown pinned commit: `fb7a865ef5eba4081dfd4e20a894a61ef7a2edca` (`v7.2.4` at staging time)
- Turndown license: MIT
- Turndown generated fixture path: `tests/conformance/fixtures/turndown/`
- Turndown attendant repository: <https://github.com/mixmark-io/turndown-attendant>
- Turndown attendant pinned commit: `651033cae3862b2fadea2f778ab7902ca5f3eee8` (`v0.0.3` at staging time)
- Turndown attendant license: MIT
- Turndown attendant generated fixture path: `tests/conformance/fixtures/turndown-attendant/`
- Local staged count: 147 `turndown-attendant` cases in `test/index.html`.
- Corpus format: each case is a `<div class="case" data-name="...">` with nested `<div class="input">` and `<pre class="expected">` nodes, plus optional `data-options`.
- Expected-output policy: exact-output for simple CommonMark cases; semantic rendered-HTML comparison for style/whitespace-sensitive cases.

### Layer 3: Pandoc as an oracle and edge-case corpus

- Repository: <https://github.com/jgm/pandoc>
- Pinned commit: `850c7b9613aa7beb1aed8c2c1f7abb01eaf3023e`
- License: GPL-2.0-or-later for the copied Pandoc test/source fixtures.
- Generated fixture path: `tests/conformance/fixtures/pandoc/`
- Selected paths include `test/Tests/Readers/HTML.hs`, `test/Tests/Writers/HTML.hs`, 8 standalone `.html` fixtures under `test/`, HTML templates, and `COPYING.md`.
- Expected-output policy: never compare byte-for-byte against Pandoc Markdown. Use Pandoc for oracle comparisons on hard HTML structures and compare normalized rendered HTML/DOM plus structural invariants.

### Layer 4: CommonMark emitted-Markdown validation, not HTML→Markdown conformance

- Repository: <https://github.com/commonmark/commonmark-spec>
- Pinned commit: `3da939428d80f146f270cd1765e4ba462e96bb1b`
- Spec version: `0.31.2`
- License: spec text is CC-BY-SA-4.0; test software is BSD-style per upstream `LICENSE`.
- Generated fixture path: `tests/conformance/fixtures/commonmark-spec/`
- Selected paths: `spec.txt`, `test/spec_tests.py`, `test/normalize.py`, `LICENSE`.
- Local staged count: 655 CommonMark examples in `spec.txt`.
- Expected-output policy: CommonMark tests are Markdown→HTML tests, so they are not direct HTML→Markdown fixtures. Use them to verify emitted Markdown is parseable and stable under Markdown→HTML normalization.

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
- Phase-2 conformance source SHAs are now staged in `tests/conformance/sources.toml`; generated fixtures are verified by `tests/conformance/fixtures.lock.json`.
