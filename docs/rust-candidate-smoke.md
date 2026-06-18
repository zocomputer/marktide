# Rust HTML→Markdown candidate dependency smoke test

Date: 2026-06-17
Agent: coder-3-leaf

Goal: de-risk installing and calling the three Rust-backed Python HTML→Markdown candidates in this repo's `uv` environment before building `benchmarks/`.

Fixture used for all candidates:

```html
<h1>hi</h1><p>x</p>
```

## Results

| Package added to `[dependency-groups].benchmark` | Installed version | Import module | Trivial API call | Output | Notes |
| --- | ---: | --- | --- | --- | --- |
| `htmd-py` | `0.1.2` | `htmd` | `htmd.convert_html(html)` | `# hi\n\nx` | API returns a plain `str`; no trailing newline for this fixture. |
| `html-to-markdown` | `3.5.7` | `html_to_markdown` | `html_to_markdown.convert(html).content` | `# hi\n\nx\n` | `convert` returns a `ConversionResult`; markdown is in the `.content` attribute. Pinned below `3.6.13` for supply-chain cooldown; `3.6.13` also smoke-tested cleanly. |
| `html2text_rs` | `0.2.5` | `html2text_rs` | `html2text_rs.text_markdown(html)` | `# hi\n\nx\n` | Accepts `str`; rejects `bytes` with `TypeError`. Also exposes `text_plain` and `text_rich`. |

All three candidates installed successfully in the repo `.venv`, imported successfully, and produced markdown for the trivial fixture.

## Dependency placement

The candidate libraries are benchmark-only competitors, not runtime dependencies of `html2md`. They live in `pyproject.toml` under `[dependency-groups].benchmark`; `pyproject.toml` keeps `[project].dependencies` to `lxml` only.

## Commands run

```bash
uv add --group benchmark htmd-py
uv run python - <<'PY'
import htmd
print(repr(htmd.convert_html('<h1>hi</h1><p>x</p>')))
PY

uv add --group benchmark html-to-markdown
uv run python - <<'PY'
import html_to_markdown
print(repr(html_to_markdown.convert('<h1>hi</h1><p>x</p>').content))
PY

uv add --group benchmark html2text_rs
uv run python - <<'PY'
import html2text_rs
print(repr(html2text_rs.text_markdown('<h1>hi</h1><p>x</p>')))
PY
```


## Streaming / incremental API and GIL probe

Question: can any candidate replace phase 2 by exposing a Python streaming/incremental/chunked HTML→Markdown API, and does the Rust work stay async-friendly when called from a worker thread / `asyncio.to_thread`?

Short answer: **no candidate exposes a Python streaming feed API**. `html2text_rs` is the only candidate whose binding releases the GIL around the full Rust conversion, but it still accepts a complete Python `str` and returns a complete Python `str` in one call. `htmd-py` and `html-to-markdown` are one-shot and hold the GIL for the whole conversion in the current Python bindings.

| Candidate | Python API shape | Streaming / feed exposed? | Binding GIL behavior | Heartbeat result on ~4.19 MiB fixture | Decision impact |
| --- | --- | --- | --- | --- | --- |
| `htmd-py==0.1.2` | `htmd.convert_html(html: str, options=None) -> str` | No. Source exposes only `convert_html` and `create_options_with_skip_tags`. | No `Python::detach` / `Python::allow_threads` around `converter.convert(html)` / `htmd_convert(html)`. | Worker thread still starves main asyncio heartbeat: p50 `133.948ms`, p95 `136.916ms`, max `136.916ms`. | Fast comparison candidate only; not async-friendly enough to remove phase 2. |
| `html-to-markdown==3.5.7` | `html_to_markdown.convert(html: str, options=None, visitor=None) -> ConversionResult`, markdown at `.content` | No. Installed Python wrapper and generated `.pyi` expose only whole-string `convert`. | No `Python::detach` / `Python::allow_threads` around `html_to_markdown_rs::convert(&html, Some(options_core))`. | Worker thread still starves main asyncio heartbeat: p50 `510.276ms`, p95 `515.621ms`, max `515.621ms`. | Strong semantic/perf comparison candidate, but current Python binding is not async-friendly. |
| `html2text_rs==0.2.5` | `html2text_rs.text_markdown(html: str, width=100) -> str` | No. Stub exposes only `text_markdown`, `text_plain`, `text_rich`; `bytes` input is rejected. | Yes. Source wraps the Rust `from_read(html_cow.as_bytes(), width)` call in `py.detach(...)`. | Worker thread is near idle heartbeat: p50 `0.271ms`, p95 `0.283ms`, p99 `2.665ms`, max `3.483ms`. | Useful async-friendly baseline, but one-shot whole-string input/output and lower Markdown fidelity mean it does not replace a streaming converter. |

Probe controls on the same machine / fixture:

| Workload | p50 heartbeat jitter | p95 heartbeat jitter | max heartbeat jitter |
| --- | ---: | ---: | ---: |
| Idle heartbeat | `0.284ms` | `0.315ms` | `6.861ms` |
| Pure-Python loop control | `13.690ms` | `15.331ms` | `16.522ms` |

Evidence checked:

- `/tmp/html2md-candidate-src/htmd/src/lib.rs:10-35` defines `fn convert_html(html: &str, options: Option<PyOptions>) -> PyResult<String>` and directly calls `converter.convert(html)` / `htmd_convert(html)` with no detach/allow_threads wrapper.
- `/Users/dcosson/h2home/projects/new-html-parser/.venv/lib/python3.12/site-packages/html_to_markdown/api.py:150-158` and `/Users/dcosson/h2home/projects/new-html-parser/.venv/lib/python3.12/site-packages/html_to_markdown/_html_to_markdown.pyi:719-723` expose only whole-string `convert(html: str, ...) -> ConversionResult`.
- `/tmp/html2md-candidate-src/html-to-markdown-v3.5.7/crates/html-to-markdown-py/src/lib.rs:2747-2769` implements Python `convert(html: String, ...)` by calling `html_to_markdown_rs::convert(&html, Some(options_core))` directly, with no detach/allow_threads wrapper.
- `/Users/dcosson/h2home/projects/new-html-parser/.venv/lib/python3.12/site-packages/html2text_rs/html2text_rs.pyi:1-3` exposes only `text_markdown`, `text_plain`, and `text_rich` whole-string functions.
- `/tmp/html2md-candidate-src/html2text_rs/src/lib.rs:11-18` implements `text_markdown` by converting the Python string to a cow and calling `py.detach(|| from_read(html_cow.as_bytes(), width))`, which explains the near-idle heartbeat.
