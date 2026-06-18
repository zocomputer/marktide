# html2md

Fast, streaming HTML → Markdown conversion for Python, built on **lxml** (C, releases
the GIL) instead of BeautifulSoup. Designed to parse large HTML incrementally — like a
browser — and emit Markdown in chunks without blocking the asyncio event loop.

> Status: early. See `docs/` for the design doc and test plan, and `benchmarks/` for the
> phase-1 comparison harness against `markdownify`, a Rust crate, and raw `lxml`.

## Why

`markdownify` is BeautifulSoup-based: slow on large inputs and it holds the GIL, so it
stalls async I/O. This library uses lxml's C parser (which releases the GIL during parse)
on a worker thread, with incremental/streaming conversion.
