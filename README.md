# marktide

Fast, streaming **HTML → Markdown** for Python — **sync *and* async** — built on **lxml**
(C, releases the GIL) instead of BeautifulSoup. A near drop-in replacement for
[`markdownify`](https://pypi.org/project/markdownify/) with markdownify-compatible options and
output (a few [documented divergences](docs/usage.md#documented-divergences) aside), but it
parses large HTML incrementally — like a browser — and emits Markdown without stalling the
asyncio event loop. First-class `async`/`await` and streaming APIs keep the loop responsive on
documents of any size.

```python
import marktide

marktide.convert("<h1>Hello</h1><p>A <b>bold</b> word and a <a href='https://x.com'>link</a>.</p>")
# 'Hello\n=====\n\nA **bold** word and a [link](https://x.com).'
```

## Install

```bash
pip install marktide
```

Requires Python 3.11+. The only runtime dependency is `lxml`.

## Why

`markdownify` is BeautifulSoup-based: it is slow on large inputs and, because it is pure
Python, it **holds the GIL** for the whole conversion. Inside an async server that means one
conversion stalls every other coroutine on the event loop — health checks time out, SSE
streams stutter, unrelated requests queue.

`marktide` drives **lxml's C parser**, which releases the GIL while it tokenizes, on a worker
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
import asyncio, marktide

# sync
md = marktide.convert("<p>hi</p>")

# async (does not block the event loop)
md = asyncio.run(marktide.convert_async("<p>hi</p>"))

# streaming: feed byte chunks, get Markdown chunks whose concatenation is the document
for piece in marktide.convert_stream([b"<ul><li>a</li>", b"<li>b</li></ul>"]):
    ...   # '* a\n* b'
```

`html` may be `str` or `bytes`. Pass `bytes` when you have them — lxml detects the encoding
from the document and skips a decode pass.

## Running in production

In async code, prefer the async entry points — they already offload the (GIL-holding) emit
work to a worker thread via `asyncio.to_thread`, so the event loop keeps running:

- **`convert_stream_async`** for unknown or large input — the loop never stalls, memory stays
  bounded, and Markdown starts flowing within milliseconds.
- **`convert_async`** when you just want the whole string and don't need streaming — the same
  loop-friendliness, simpler call.

```python
md = await convert_async(html)                       # whole string, off the loop
async for piece in convert_stream_async(chunks):     # streamed, bounded memory
    ...
```

**Don't call the synchronous APIs — `convert()` *or* `convert_stream()` — on the event loop.**
Both run on the loop's *own* thread: `convert()` blocks it for the whole conversion (seconds on
a 100 MiB document), and iterating `convert_stream()` blocks it for each chunk's feed-and-emit.
lxml releasing the GIL helps *other* threads, not the loop thread that is running the
conversion. Reserve the sync APIs (`convert` / `convert_stream`) for non-async contexts
(scripts, workers, sync web handlers); in async code use `convert_async` / `convert_stream_async`.

You generally don't need to branch on input size: the `asyncio.to_thread` dispatch is
sub-millisecond, so routing everything through `convert_async` / `convert_stream_async` in
async code is fine.

## Options & markdownify compatibility

Pass an `Options` for non-default rendering, or `markdownify_compat(**kwargs)` to reuse your
existing `markdownify` keyword arguments verbatim:

```python
from marktide import convert, Options, markdownify_compat

convert("<h1>Hello</h1>", options=Options(heading_style="atx"))            # '# Hello'
convert("<h1>Hello</h1>", options=markdownify_compat(heading_style="atx")) # '# Hello'
```

Defaults are identical to `markdownify==1.2.2` (setext `h1`/`h2`, `*` emphasis, two-space
`<br>`, `*+-` depth bullets). See **[docs/usage.md](docs/usage.md)** for the full options
table, every public function in detail, and a **migrating-from-markdownify** guide.

## Correctness & conformance

marktide is validated against a **1107-case differential suite**: each HTML input is converted
by marktide and by an oracle, and the results are compared. It has two tiers.

**Primary — the markdownify drop-in contract (298 cases).** markdownify's own test suite
(234 cases) plus a hand-authored per-handler + edge-case golden corpus (64 cases), checked
against `markdownify==1.2.2`. marktide passes **296/298 raw (99.3%)** and **298/298 effective
(100%)**; the two raw misses are [documented divergences](docs/usage.md#documented-divergences)
on invalid nested-block-in-heading markup, where lxml's HTML tree construction differs from
markdownify's BeautifulSoup parser. `convert` and `convert_stream` agree on **0/1107** cases
(exact streaming parity).

**Guardrail / triangulation (809 cases).** Diverse HTML inputs drawn from the Turndown (147),
CommonMark spec (654), and Pandoc (8) test suites — real-world fragments beyond what the
markdownify suite covers. marktide's output is compared to the markdownify oracle on the same
input after normalization (collapsing incidental blank-line/whitespace differences); the
CommonMark layer adds a stricter *semantic* check that renders both outputs back to HTML and
compares the structure. These catch regressions the curated markdownify cases alone would miss.

The external corpora are pulled from their upstream projects and **pinned to immutable
commits** in [`tests/conformance/sources.toml`](tests/conformance/sources.toml), regenerated
deterministically by `scripts/regenerate_conformance_corpus.py`; the 64-case golden set is
hand-authored (oracle-generated) under `tests/conformance/golden/`. Reproduce locally:

```bash
make verify-fidelity   # primary drop-in fidelity: raw/effective counts, parity, divergences
make conformance       # the full 1107-case differential suite
make verify-canonical  # semantic equivalence on examples/canonical.html/.md
```

For a small human-readable smoke example, see [examples/canonical.html](examples/canonical.html)
and the committed marktide output [examples/canonical.md](examples/canonical.md).
`make verify-canonical` render-normalizes that example across marktide, markdownify,
html-to-markdown, and pandoc when installed.

Separately, the e2e suite and benchmarks run on **real-world HTML fixtures up to ~110 MiB**
(Wikipedia / RFC / gov pages, pinned in `benchmarks/fixtures.lock.json`) to exercise the
streaming path, huge-document handling (`huge_tree`), and `convert == convert_stream` at scale.

## Compatibility & edge cases

The markdownify drop-in contract is the primary guarantee — **296/298 raw, 298/298 effective**
(`make verify-fidelity`). The cases that differ are edge/guardrail behaviors — some on
invalid HTML, others convention or whitespace-normalization choices on valid HTML. A
representative selection is shown below as *input → marktide → markdownify* (not exhaustive; the
guardrail layers carry a few more, all non-primary).

**Parser divergences (the 2 primary effective-pass cases).** marktide parses with lxml;
markdownify uses BeautifulSoup's `html.parser`. The two HTML parsers build different trees for
*invalid* markup, and which one matches the HTML5 spec depends on the case:

| Input | marktide | markdownify | Why |
|---|---|---|---|
| `<h1>A <p>P</p> C </h1>` (ATX) | `# A`, then `P`, then `C` | `# A P C` | A `<p>` can't nest in a heading (non-conforming input). The HTML5 algorithm does *not* close the heading here — `html5lib` and `html.parser` keep the `<p>` inside the `<h1>`, so markdownify flattens it into the heading text. lxml/libxml2 uses a custom, documented non-HTML5 tree builder that auto-closes the `<h1>`, so marktide sees a heading plus a sibling paragraph. (Here lxml is the one that diverges from HTML5.) |

**Guardrail edge cases** (from the Turndown / Pandoc / CommonMark corpora — not the primary
contract):

| Input | marktide | markdownify | Why |
|---|---|---|---|
| `<strike>bar</strike>` | `~~bar~~` | `bar` | marktide treats `<strike>` as a strikethrough alias of `<s>`/`<del>`; markdownify 1.2.2 strikethroughs only `<s>`/`<del>`. |
| `<h7>Heading?</h7>` | `Heading?` | `###### Heading?` | `<h7>` is not a real tag; lxml leaves it transparent (so does Turndown), markdownify coerces it to an h6. |
| `<p>Foo<span> </span>Bar</p>` | `FooBar` | `Foo Bar` | A `<span>` containing only collapsible ASCII whitespace: marktide drops it, markdownify keeps one separating space. |
| `<p>Foo<span>  &nbsp;  </span>Bar</p>` | `'Foo \xa0Bar'` (NBSP, no space) | `'Foo \xa0 Bar'` (NBSP + space) | Mixed ASCII + NBSP in a whitespace-only span: marktide preserves the NBSP but drops the ASCII space after it. |
| `<p>foo <![CDATA[>&<]]></p>` | `foo &<]]>` | `foo >&<` | `<![CDATA[` in HTML content isn't a real CDATA section — the HTML5 tokenizer treats it as a bogus comment, and the `>` after `[CDATA[` ends it, leaving `&<]]>` as text. `html5lib` and lxml agree (lxml is HTML5-correct here); markdownify's `html.parser` instead preserves the raw `>&<` source text. |

Of these, the two parser-divergence cases (`<h1>`-nesting) and the CDATA case are recorded in
[`tests/conformance/allowed_divergences.toml`](tests/conformance/allowed_divergences.toml) and
surfaced by `make verify-fidelity`. The `<strike>`/`<h7>`/whitespace-span rows are
guardrail-layer convention differences against the markdownify oracle, not part of the primary
contract and not in that ledger.

**Optional: `commonmark_roundtrip_stable`.** Inline code-span delimiters are markdownify-exact
by default (longest backtick run + 1, padded when the content has any backtick). Set
`Options(commonmark_roundtrip_stable=True)` to instead use canonical CommonMark delimiters
(the smallest absent run length, padded only at the edges), which keeps generated Markdown
*textually* stable across a CommonMark render→convert round-trip (e.g. adjacent code spans like
`<code>0</code><code>0</code>`). Leave it off for strict markdownify-output compatibility; the
default never changes fidelity.

## Benchmarks

marktide set out to replace `markdownify` on **five axes at once** — fast, async-friendly,
streaming, bounded-memory, and faithful. The phase-3 comparison shows no existing library
clears all five: `htmd_py` is faster in raw wall time but stalls the event loop, `html2text_rs`
is also faster but lower-fidelity, and `html_to_markdown` is roughly tied with marktide on wall
time yet still stalls the loop — and all of them use multiple GiB of memory and can't stream.
markdownify is faithful but slow and GIL-bound.

### Phase-3 results — `xlarge` fixture (~110 MiB document)

| Library | Wall time | vs markdownify | Peak RSS growth | Missed event-loop beats | Time-to-first-chunk | Streams? |
|---|--:|--:|--:|--:|--:|:--:|
| `markdownify` (incumbent) | 54.55 s | 1.0× | 2811.1 MiB | 60.4% | — | no |
| `html_to_markdown` (Rust) | 4.78 s | 11.4× | 3761.0 MiB | 50.0% | — | no |
| `htmd_py` (Rust) | 1.71 s | 31.8× | 1569.2 MiB | 50.0% | — | no |
| `html2text_rs` (Rust) | 3.03 s | 18.0× | 3906.7 MiB | 0.4% | — | no |
| **`marktide` (streaming)** | **4.73 s** | **11.5×** | **247.3 MiB** | **0.0%** | **2.2 ms** | **yes** |

Reading it: marktide converts the 110 MiB document **11.5× faster than markdownify** while using
**11.4× less peak memory** and **never starving the event loop** (0% missed heartbeat beats vs
markdownify's 60%). Two Rust one-shots post lower raw wall times (`htmd_py`, `html2text_rs`;
`html_to_markdown` is roughly tied), but each fails a different axis: `html_to_markdown` and
`htmd_py` **hold the GIL** (~50% missed beats; p99 event-loop stalls of 1.7–4.8 s),
`html2text_rs` releases the GIL (0.4% missed) but is **low-fidelity** (drops formatting), and
all three use **6–15× more memory than marktide** and
**cannot stream**. marktide is the only contender that is *simultaneously* fast-enough,
async-friendly, streaming, memory-bounded, and faithful (**99.3% raw / 100% effective**
normalized conformance against the markdownify oracle, with two
[documented divergences](docs/usage.md#documented-divergences)).

- **Async-friendly** — fraction of 5 ms event-loop heartbeats missed while a conversion runs on
  a worker thread: marktide 0.0%, markdownify 60.4%, `html_to_markdown`/`htmd_py` ~50%,
  `html2text_rs` 0.4%.
- **Streaming** — marktide emits the first Markdown chunk after **2.2 ms** and sustains output
  across the document; one-shot libraries emit only after the full conversion finishes.
- **Bounded scaling** — marktide's peak RSS grows **sub-linearly**: its peak-RSS-to-input ratio
  falls from 7.7× (small) to **2.3× (xlarge)**, while markdownify's stays ~**26× at every size**
  (linear growth). On the 110 MiB input that puts marktide's growth (247.3 MiB) **11.4× below**
  markdownify's 2811.1 MiB — because the streaming path builds no full DOM and drains completed
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
uv run bench-async-starvation  # markdownify vs marktide_streaming heartbeat proof only
```

`uv run bench --full` writes the phase-3 matrix to `benchmarks/results/`; the committed
canonical results are `benchmarks/results/phase3.json` and `benchmarks/results/report.md`.

## Status & docs

- **[docs/usage.md](docs/usage.md)** — full usage & migration guide
- **[docs/design.md](docs/design.md)** — architecture, the GIL/streaming story, test strategy
- **[docs/test-plan.md](docs/test-plan.md)** — the test harness
- **[examples/README.md](examples/README.md)** — examples including [examples/canonical.html](examples/canonical.html) and the committed marktide output [examples/canonical.md](examples/canonical.md)

Early but functional. The conversion handlers match `markdownify` across the bulk of its own
test suite (a few edge cases — e.g. lossy tables, CDATA, invalid nested markup — are
[documented divergences](docs/usage.md#documented-divergences) or in progress); the streaming
and async paths are validated end-to-end.
