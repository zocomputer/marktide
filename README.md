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

## Benchmarks

html2md set out to replace `markdownify` on **five axes at once** — fast, async-friendly,
streaming, bounded-memory, and faithful. The phase-3 comparison shows no existing library
clears all five: the faithful Rust converters (`htmd_py`, `html_to_markdown`) are faster in raw
wall time but stall the event loop; `html2text_rs` stays responsive but is lower-fidelity; and
all of them use multiple GiB of memory and can't stream. markdownify is faithful but slow and
GIL-bound.

### Phase-3 results — `xlarge` fixture (~110 MiB document)

| Library | Wall time | vs markdownify | Peak RSS growth | Missed event-loop beats | Time-to-first-chunk | Streams? |
|---|--:|--:|--:|--:|--:|:--:|
| `markdownify` (incumbent) | 53.44 s | 1.0× | 2808.9 MiB | 70.0% | — | no |
| `html_to_markdown` (Rust) | 4.57 s | 11.7× | 4306.6 MiB | 50.0% | — | no |
| `htmd_py` (Rust) | 1.63 s | 32.8× | 1569.1 MiB | 50.0% | — | no |
| `html2text_rs` (Rust) | 2.89 s | 18.5× | 3905.5 MiB | 0.4% | — | no |
| **`html2md` (streaming)** | **5.99 s** | **8.9×** | **244.7 MiB** | **0.0%** | **2.4 ms** | **yes** |

Reading it: html2md converts the 110 MiB document **8.9× faster than markdownify** while using
**11.5× less peak memory** and **never starving the event loop** (0% missed heartbeat beats vs
markdownify's 70%). The Rust one-shot libraries post lower raw wall times, but each fails a
different axis: `html_to_markdown` and `htmd_py` **hold the GIL** (~50% missed beats; p99
event-loop stalls of 1.6–4.6 s), `html2text_rs` releases the GIL (0.4% missed) but is
**low-fidelity** (drops formatting), and all three use **6–18× more memory than html2md** and
**cannot stream**. html2md is the only contender that is *simultaneously* fast-enough,
async-friendly, streaming, memory-bounded, and faithful (**99.3% raw / 100% effective**
normalized conformance against the markdownify oracle, with two
[documented divergences](docs/usage.md#documented-divergences)).

- **Async-friendly** — fraction of 5 ms event-loop heartbeats missed while a conversion runs on
  a worker thread: html2md 0.0%, markdownify 70.0%, `html_to_markdown`/`htmd_py` ~50%,
  `html2text_rs` 0.4%.
- **Streaming** — html2md emits the first Markdown chunk after **2.4 ms** and sustains output
  across the document; one-shot libraries emit only after the full conversion finishes.
- **Bounded scaling** — html2md's peak RSS grows **sub-linearly**: its peak-RSS-to-input ratio
  falls from 7.7× (small) to **2.2× (xlarge)**, while markdownify's stays ~**25× at every size**
  (linear growth). On the 110 MiB input that puts html2md's growth (244.7 MiB) **11.5× below**
  markdownify's 2808.9 MiB — because the streaming path builds no full DOM and drains completed
  blocks rather than holding the whole document. See
  `benchmarks/results/charts/memory_scaling_peak_rss.png`.

**Verifying fidelity:** run `make verify-fidelity` from the repository root — it prints the
raw/effective conformance counts (296/298 = 99.3% raw, 298/298 = 100% effective), per-oracle
rows, streaming parity (0/1107 mismatches), and the active documented divergences. Details in
[`tests/conformance/README.md`](tests/conformance/README.md).

### How we ran them

Fixtures are the `small` (100 KiB), `medium` (5 MiB), `large` (50 MiB), and `xlarge` (110 MiB)
documents recorded in `benchmarks/fixtures.lock.json` (real Wikipedia / RFC / gov pages,
regenerated by `scripts/regenerate_benchmark_fixtures.py`). The async-starvation / heartbeat
measurement (a background asyncio heartbeat sampled while each conversion runs on a worker
thread) lives in `benchmarks/harness/probe.py`, not in the e2e suite.

The benchmark harness is a self-contained uv project under `benchmarks/`:

```bash
cd benchmarks && uv sync
uv run bench                    # quick check: small+medium, all 7 contenders, async headline
uv run bench --full            # full small→xlarge phase-3 matrix + charts
uv run bench-async-starvation  # markdownify vs html2md_streaming heartbeat proof only
```

`uv run bench --full` writes the phase-3 matrix to `benchmarks/results/`; the committed
canonical results are `benchmarks/results/phase3.json` and `benchmarks/results/report.md`.

## Status & docs

- **[docs/usage.md](docs/usage.md)** — full usage & migration guide
- **[docs/design.md](docs/design.md)** — architecture, the GIL/streaming story, test strategy
- **[docs/test-plan.md](docs/test-plan.md)** — the test harness

Early but functional. The conversion handlers match `markdownify` across the bulk of its own
test suite (a few edge cases — e.g. lossy tables, CDATA, invalid nested markup — are
[documented divergences](docs/usage.md#documented-divergences) or in progress); the streaming
and async paths are validated end-to-end.
