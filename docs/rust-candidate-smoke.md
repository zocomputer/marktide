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
| `html-to-markdown` | `3.6.13` | `html_to_markdown` | `html_to_markdown.convert(html).content` | `# hi\n\nx\n` | `convert` returns a `ConversionResult`; markdown is in the `.content` attribute. |
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
