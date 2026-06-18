# html2md — Usage & Migration Guide

`html2md` converts HTML to Markdown with `markdownify==1.2.2`-compatible output, on top of
lxml's streaming C parser. This guide covers the public API, the full options surface, and
how to migrate from `markdownify`.

- [Install](#install)
- [The four public functions](#the-four-public-functions)
- [Input: str vs bytes](#input-str-vs-bytes)
- [Options](#options)
- [`markdownify_compat`](#markdownify_compat)
- [Migrating from markdownify](#migrating-from-markdownify)
- [Why lxml / streaming](#why-lxml--streaming)

## Install

```bash
pip install html2md
```

Requires Python 3.11+. The only runtime dependency is `lxml` (>= 5).

```python
import html2md
from html2md import convert, convert_async, convert_stream, convert_stream_async
from html2md import Options, markdownify_compat
```

## The four public functions

All four take the same `html` input and an optional `options=Options(...)`.

### `convert(html, *, options=None) -> str`

One-shot, synchronous — the common case.

```python
convert("<h1>Hello</h1><p>A <b>bold</b> word and a <a href='https://x.com'>link</a>.</p>")
# 'Hello\n=====\n\nA **bold** word and a [link](https://x.com).'
```

### `async convert_async(html, *, options=None) -> str`

Same result as `convert`, but the conversion runs on a worker thread so it does **not** block
the event loop. Use this in async request handlers.

```python
import asyncio
asyncio.run(convert_async("<p>hi</p>"))   # 'hi'
```

### `convert_stream(chunks, *, options=None) -> Iterator[str]`

Feed an iterable of **byte** chunks; get an iterator of Markdown chunks. The concatenation of
the yielded chunks equals `convert` of the whole document — you can split the input bytes
anywhere. Use this for large documents to keep memory bounded.

```python
list(convert_stream([b"<ul><li>a</li>", b"<li>b</li></ul>"]))
# ['* a\n* b']

# stream a file without loading it all into memory:
def file_chunks(path, size=64 * 1024):
    with open(path, "rb") as f:
        while chunk := f.read(size):
            yield chunk

markdown = "".join(convert_stream(file_chunks("big.html")))
```

### `async convert_stream_async(chunks, *, options=None) -> AsyncIterator[str]`

The async streaming path: takes an **async** iterable of byte chunks and yields Markdown
chunks. The worker thread feeds the parser and the event loop is awaited between chunks, so
the loop stays responsive and consumers see output before the input is fully read.

```python
async def main():
    async def chunks():
        yield b"<h1>Hi</h1>"
        yield b"<p>there</p>"
    return [piece async for piece in convert_stream_async(chunks())]

asyncio.run(main())   # ['Hi\n==', '\n\nthere']   →  concatenation is the full document
```

## Input: str vs bytes

`html` accepts `str` or `bytes`.

- **`bytes`** is preferred when you already have them (e.g. an HTTP response body): lxml
  detects the encoding from the document's declaration and converts in C without a Python
  decode pass.

  ```python
  convert(b"<p>caf\xc3\xa9</p>")   # 'café'   (UTF-8 decoded by lxml)
  ```

- **`str`** is encoded to UTF-8 before parsing.

The streaming functions always take **byte** chunks (split the encoded bytes however you
like).

## Options

`Options` is an immutable dataclass whose field names and defaults are **identical to
`markdownify==1.2.2`**, plus html2md-specific fields. Construct one and pass it as
`options=`.

| Option | Default | Meaning |
|---|---|---|
| `autolinks` | `True` | Emit `<url>` when a link's text equals its href. |
| `bullets` | `"*+-"` | Unordered-list markers, chosen by nesting depth. |
| `heading_style` | `"underlined"` | `"underlined"` (setext `h1`/`h2`), `"atx"` (`#`), or `"atx_closed"` (`# … #`). |
| `strong_em_symbol` | `"*"` | `"*"` or `"_"` for emphasis/strong. |
| `newline_style` | `"spaces"` | `<br>` → two trailing spaces (`"spaces"`) or `\` (`"backslash"`). |
| `escape_asterisks` | `True` | Escape literal `*` in text. |
| `escape_underscores` | `True` | Escape literal `_` in text. |
| `escape_misc` | `False` | Escape other Markdown-significant characters. |
| `code_language` | `""` | Default fence info string for `<pre>` blocks. |
| `code_language_callback` | `None` | `callable(element) -> str` to derive a fence language. |
| `strip` | `None` | Tags to render as their children only (markup dropped). |
| `convert` | `None` | Allow-list of tags to convert (mutually exclusive with `strip`). |
| `keep_inline_images_in` | `()` | Parent tags in which inline images keep `![…]` form. |
| `default_title` | `False` | Use the href as the link title when none is given. |
| `sub_symbol` / `sup_symbol` | `""` | Wrap `<sub>` / `<sup>` content (e.g. `"~"`, `"^"`). |
| `strip_document` | `"strip"` | Trim document-level newlines: `"strip"`, `"lstrip"`, `"rstrip"`, or `None`. |
| `strip_pre` | `"strip"` | Trim newlines around `<pre>`: `"strip"`, `"strip_one"`, or `None`. |
| `table_infer_header` | `False` | Treat a header-less first row as the table header. |
| `wrap` / `wrap_width` | `False` / `80` | Hard-wrap paragraph text at `wrap_width` columns. |
| **`chunk_size`** | `65536` | *(html2md)* Feed granularity for the streaming/async paths. |
| **`default_encoding`** | `"utf-8"` | *(html2md)* Encoding used when encoding `str` input. |
| **`commonmark_roundtrip_stable`** | `False` | *(html2md)* Optional canonical code-span delimiter policy for CommonMark render→convert text stability. Default `False` preserves markdownify fidelity. |

```python
from html2md import convert, Options

convert("<h1>Hi</h1>", options=Options(heading_style="atx"))                # '# Hi'
convert("<p>a<br>b</p>", options=Options(newline_style="backslash"))       # 'a\\\nb'
convert("<ul><li>x</li></ul>", options=Options(bullets="-"))               # '- x'
convert("<p><code>0</code><code>0</code></p>",
        options=Options(commonmark_roundtrip_stable=True))                  # '`0``0`'
```

`strip` and `convert` are mutually exclusive — constructing `Options` with both set raises
`ValueError`, matching markdownify.

## `markdownify_compat`

If you already call `markdownify(html, **kwargs)`, pass the same keyword arguments to
`markdownify_compat` to get an equivalent `Options`:

```python
from html2md import convert, markdownify_compat

# was: markdownify(html, heading_style="atx", strong_em_symbol="_")
convert(html, options=markdownify_compat(heading_style="atx", strong_em_symbol="_"))
```

It accepts every `markdownify==1.2.2` keyword under its identical name. It raises `ValueError`
for the two things html2md cannot honour:

- **`bs4_options`** — html2md drives lxml, not BeautifulSoup, so this option is meaningless.
- **`strip` + `convert` together** — mutually exclusive (same as markdownify).

```python
markdownify_compat(bs4_options="html.parser")
# ValueError: bs4_options is not supported: html2md uses lxml, not BeautifulSoup; remove this kwarg
```

## Migrating from markdownify

`html2md` is designed as a near drop-in replacement (see [Documented
divergences](#documented-divergences) for the exceptions). In most code the change is:

```python
# before
from markdownify import markdownify
md = markdownify(html, heading_style="atx")

# after
from html2md import convert, markdownify_compat
md = convert(html, options=markdownify_compat(heading_style="atx"))
```

### What's identical

Option names and defaults match `markdownify==1.2.2`, and rendered Markdown matches across the
bulk of markdownify's own test suite (`test_conversions`, `test_basic`, `test_advanced`,
`test_lists`, …) and a layered HTML→Markdown conformance corpus. Headings, emphasis, links,
images, code spans, lists (including nested indentation and ordered `start`), blockquotes,
definition lists, `<br>`, and the dropped tags (`<script>`/`<style>`) behave the same. A few
edge cases differ — see below.

### Documented divergences

Conformance is high but not yet 100%; the known intentional differences are:

- **Invalid nested block-in-heading** (e.g. `<p>` inside `<h1>`). html2md parses HTML with
  lxml, which constructs the tree the way a browser does — it auto-closes the `<h1>` before
  the `<p>`. markdownify's BeautifulSoup `html.parser` keeps the `<p>` nested. For valid HTML
  this never arises; for invalid HTML html2md follows the browser/standards behavior.
- **Lossy tables** (`colspan`, ragged rows, header-less first rows). Markdown pipe tables
  cannot encode these faithfully; html2md's handling of such tables may differ from
  markdownify's synthetic-cell output. Prefer explicit, valid table markup.
- **CDATA sections** and a small number of other whitespace/edge cases are still being
  reconciled against the oracle.

The reviewed intentional divergences are tracked in
`tests/conformance/allowed_divergences.toml`; the remaining gaps are tracked as open
conformance work.

### What you gain

- `convert_async` doesn't block the event loop (markdownify, being pure Python, holds the
  GIL even on a worker thread).
- `convert_stream` / `convert_stream_async` give bounded memory and early output on large
  documents — markdownify is whole-document only.

## Why lxml / streaming

`markdownify` is BeautifulSoup-based: slow on large inputs and it holds the GIL, so a
conversion inside an async server stalls every other coroutine. `html2md` drives lxml's
incremental **target parser** (SAX-like, no DOM) on a worker thread. lxml releases the GIL
while it tokenizes each fed chunk, and the Markdown emitter runs as a deterministic
transducer over the event stream, so:

- memory is bounded by the parser's open-element state plus the largest currently-open block
  or table — completed blocks are drained as they close, so a 100 MB document of
  normal-sized blocks stays flat; only a pathologically large single block/table grows it;
- the async paths keep the event loop responsive (measured: sub-2 ms p99 scheduling latency
  under load, versus hundreds of milliseconds for a GIL-bound converter);
- streaming emits Markdown for completed blocks before the input is fully read.

See [docs/design.md](design.md) for the full architecture, the GIL measurements, and the
test strategy.
