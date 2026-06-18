# Code Review: zo-1fp.12 (R1, reviewer-leaf)

- Bead: zo-1fp.12
- Commit range: ec758bb..e9cfdae
- Plan doc: docs/design.md, docs/test-plan.md
- Reviewer: reviewer-leaf
- Review commit: 896a5a1

## Findings

### P1 - `Options.wrap=True` is ignored for paragraphs

**Location:** `src/html2md/rules/blocks.py:66-77`, `tests/unit/html2md/test_block_inline_handlers.py:58-62`

**Problem**
`_Paragraph.end` strips the rendered children and emits them unchanged. Markdownify's `convert_p` applies `textwrap.fill(...)` when `wrap=True` and `wrap_width` is not `None`, preserving `<br>` newlines while wrapping long prose lines. Because the paragraph handler ignores `em.options.wrap` / `em.options.wrap_width`, any caller relying on markdownify's line wrapping gets one long unwrapped line.

Repro:

```python
html = "<p>" + "word " * 30 + "</p>"
markdownify.markdownify(html, wrap=True, wrap_width=20)
# 'word word word word\nword word word word\n...'
html2md.convert(html, options=Options(wrap=True, wrap_width=20))
# 'word word word word word word word word ...'
```

The committed golden test loop does not cover this option path, and this is not one of the acknowledged emitter/whitespace xfails.

**Suggested fix**
Port markdownify's `convert_p` wrapping branch into `_Paragraph.end`: split on existing `\n`, lstrip each line, preserve trailing whitespace, call `textwrap.fill(width=em.options.wrap_width, break_long_words=False, break_on_hyphens=False)`, then join with `\n`. Add explicit tests comparing markdownify for `wrap=True`, `wrap_width=<small>`, and a paragraph containing `<br>` so hard-break newlines remain intact.

---

### P1 - `Options.code_language_callback` is ignored for fenced `<pre>` blocks

**Location:** `src/html2md/rules/blocks.py:129-144`, `tests/unit/html2md/test_block_inline_handlers.py:58-62`

**Problem**
`_Pre.end` always uses `em.options.code_language` as the fence language. Markdownify's `convert_pre` first initializes from `code_language`, then calls `code_language_callback(el)` when present and uses the callback result if truthy. `Options.code_language_callback` is part of the committed markdownify-compatible options surface, so silently ignoring it breaks drop-in fidelity for language-class extraction.

Repro:

```python
def cb(el):
    return "PY"
html = '<pre><code class="language-py">x</code></pre>'
markdownify.markdownify(html, code_language_callback=cb)  # '```PY\nx\n```'
html2md.convert(html, options=Options(code_language_callback=cb))  # '```\nx\n```'
```

**Suggested fix**
Call `em.options.code_language_callback` from `_Pre.end` when present. Since html2md does not expose a BeautifulSoup `Tag`, define and test the documented html2md element view contract (at minimum pass `em.frame` or a small view exposing tag/attrs/content) and use `callback_result or code_language`, matching markdownify. Add a regression proving the callback overrides `code_language` when truthy and falls back when it returns an empty string.

---

### P2 - `strip_pre="strip_one"` is accepted but treated like `None`

**Location:** `src/html2md/rules/blocks.py:129-144`, `src/html2md/options.py:46-47`

**Problem**
Markdownify supports `strip_pre="strip_one"`, which removes exactly one leading and one trailing newline around preformatted content. `Options` does not document this value in its `StripMode`, but `markdownify_compat(strip_pre="strip_one")` still constructs `Options(strip_pre="strip_one")` at runtime because there is no validation. `_Pre.end` only handles `"strip"`; all other values fall through as if `strip_pre is None`, preserving too many newlines.

Repro:

```python
html = "<pre>\n\n  x\n\n</pre>"
markdownify.markdownify(html, strip_pre="strip_one")  # '```\n\n  x\n```'
html2md.convert(html, options=Options(strip_pre="strip_one"))  # '```\n\n\n  x\n\n\n```'
```

**Suggested fix**
Decide the option contract explicitly. For markdownify fidelity, add `"strip_one"` to the accepted `strip_pre` values, implement markdownify's one-newline trim behavior in `_Pre.end`, and add tests for `strip`, `strip_one`, and `None`. If html2md intentionally does not support `strip_one`, `markdownify_compat(strip_pre="strip_one")` should reject it loudly instead of silently producing different Markdown.

## Validation performed

- Read `src/html2md/rules/blocks.py`, `src/html2md/rules/inline.py`, and `tests/unit/html2md/test_block_inline_handlers.py` from commit `e9cfdae`.
- Ran `uv run pytest tests/unit/html2md/test_block_inline_handlers.py -q` → `53 passed, 10 xfailed in 0.08s`.
- Compared targeted option-sensitive block/inline behavior against `markdownify==1.2.2` with `uv run --group benchmark python`; verified the requested core paths for setext/ATX headings, two-space/backslash `<br>`, code-span backtick growth, links/autolinks, images, and nested list indentation, and found the option-path divergences listed above.
- Did not flag the 10 known emitter/parser-dependent xfails called out in `tests/unit/html2md/test_block_inline_handlers.py:28-44`.

## Summary

3 findings: 0 P0, 2 P1, 1 P2, 0 P3

**Verdict**: Not approved

The main local handler mechanics look solid for the explicitly requested default paths (underlined h1/h2, emphasis, br, code-span backticks, nested-list indentation, link/img title/autolink). The remaining issues are markdownify-compatible option paths in the block handlers: paragraph wrapping, pre language callbacks, and `strip_pre="strip_one"`.

## Disposition (R1 → R2, coder-2-leaf, commit d2f1fc5)

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | P1 | `wrap`/`wrap_width` ignored in `_Paragraph` | **Fixed** — ported markdownify's `convert_p` wrap branch (`textwrap.fill`, `break_long_words`/`break_on_hyphens` off, per-line trailing preserved). Test `test_paragraph_honours_wrap_width`. |
| 2 | P1 | `code_language_callback` ignored in `_Pre` | **Fixed** — `_Pre.end` calls `code_language_callback(em.frame)` and uses `result or code_language`. Test `test_pre_honours_code_language_callback`. |
| 3 | P2 | `strip_pre="strip_one"` treated like `None` | **Fixed (handler)** — added `_strip1_pre` (one leading/trailing newline) and the `strip_one` branch in `_Pre.end`. Test `test_strip_pre_strip_one_removes_single_newline`. **Note for options owner:** `Options.strip_pre`'s `StripMode = Literal["strip","lstrip","rstrip"]` is wrong — markdownify `strip_pre` is `strip`/`strip_one`/`None`. The handler now honours `strip_one` at runtime; the *type* annotation (in `options.py`, not this task's file) should be corrected to `Literal["strip","strip_one"] | None` by the options owner. Flagged separately.

Also folded in (markdownify_tests hardening, not R1 findings): `del`/`s`/`strike` (`~~`), `sub`/`sup` (`sub_symbol`/`sup_symbol`, incl. `<tag>`-shaped symbols). markdownify_tests pass rate (corrected measurement, see note below) 145 → 153/234.

> Measurement note for R2: markdownify's own `tests/utils.md` sets `strip_document=None` and forwards per-assert `**options`. A fidelity measurement must apply both, else default-option `convert()` mismatches every case on surrounding newlines and option paths. Raised with coder-1-leaf to fix the `load_markdownify_cases` extraction (it currently drops both → understated pass rate).
