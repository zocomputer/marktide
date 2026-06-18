# html2md

Fast, streaming **HTML → Markdown** for Python, built on **lxml** (C, releases the GIL)
instead of BeautifulSoup. A near drop-in replacement for [`markdownify`](https://pypi.org/project/markdownify/):
markdownify-compatible options and output (with a few [documented divergences](docs/usage.md#documented-divergences)),
but it parses large HTML incrementally — like a browser — and emits Markdown without stalling
the asyncio event loop.

```python
import html2md

html2md.convert("<h1>Hello</h1><p>A <b>bold</b> word and a <a href='https://x.com'>link</a>.</p>")
# 'Hello\n=====\n\nA **bold** word and a [link](https://x.com).'
```

## Install

```bash
pip install html2md
```

Requires Python 3.11+. The only runtime dependency is `lxml`.

## Why

`markdownify` is BeautifulSoup-based: it is slow on large inputs and, because it is pure
Python, it **holds the GIL** for the whole conversion. Inside an async server that means one
conversion stalls every other coroutine on the event loop — health checks time out, SSE
streams stutter, unrelated requests queue.

`html2md` drives **lxml's C parser**, which releases the GIL while it tokenizes, on a worker
thread, and emits Markdown incrementally. The result:

- **Async-friendly** — `convert_async` runs off the event loop and the loop keeps ticking.
- **Bounded memory** — the streaming path builds no full DOM and drains completed blocks as
  they close, so peak memory is bounded by the parser's open-element state plus the largest
  currently-open block or table — not the whole document.
- **Early output** — `convert_stream` yields Markdown for early blocks while the tail is
  still being read (sub-millisecond time-to-first-chunk on large docs).
- **markdownify-compatible** — option names and defaults mirror `markdownify==1.2.2`, and the
  output matches across the bulk of markdownify's own test suite and a layered conformance
  corpus, apart from a few [documented divergences](docs/usage.md#documented-divergences).

## The four public functions

| Function | Use it for |
|---|---|
| `convert(html) -> str` | One-shot, synchronous. The common case. |
| `convert_async(html) -> str` | One-shot inside async code, off the event loop. |
| `convert_stream(chunks) -> Iterator[str]` | Stream a large document; bounded memory. |
| `convert_stream_async(chunks) -> AsyncIterator[str]` | Stream inside async code. |

```python
import asyncio, html2md

# sync
md = html2md.convert("<p>hi</p>")

# async (does not block the event loop)
md = asyncio.run(html2md.convert_async("<p>hi</p>"))

# streaming: feed byte chunks, get Markdown chunks whose concatenation is the document
for piece in html2md.convert_stream([b"<ul><li>a</li>", b"<li>b</li></ul>"]):
    ...   # '* a\n* b'
```

`html` may be `str` or `bytes`. Pass `bytes` when you have them — lxml detects the encoding
from the document and skips a decode pass.

## Options & markdownify compatibility

Pass an `Options` for non-default rendering, or `markdownify_compat(**kwargs)` to reuse your
existing `markdownify` keyword arguments verbatim:

```python
from html2md import convert, Options, markdownify_compat

convert("<h1>Hello</h1>", options=Options(heading_style="atx"))            # '# Hello'
convert("<h1>Hello</h1>", options=markdownify_compat(heading_style="atx")) # '# Hello'
```

Defaults are identical to `markdownify==1.2.2` (setext `h1`/`h2`, `*` emphasis, two-space
`<br>`, `*+-` depth bullets). See **[docs/usage.md](docs/usage.md)** for the full options
table, every public function in detail, and a **migrating-from-markdownify** guide.

## Status & docs

- **[docs/usage.md](docs/usage.md)** — full usage & migration guide
- **[docs/design.md](docs/design.md)** — architecture, the GIL/streaming story, test strategy
- **[docs/test-plan.md](docs/test-plan.md)** — the test harness

Early but functional. The conversion handlers match `markdownify` across the bulk of its own
test suite (a few edge cases — e.g. lossy tables, CDATA, invalid nested markup — are
[documented divergences](docs/usage.md#documented-divergences) or in progress); the streaming
and async paths are validated end-to-end.
