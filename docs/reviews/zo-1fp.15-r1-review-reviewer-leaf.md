# Code Review: zo-1fp.15 (R1, reviewer-leaf)

- Bead: zo-1fp.15
- Commit range: 81fffed
- Plan doc: docs/design.md §11
- Reviewer: reviewer-leaf
- Review commit: 56b9ed9

## Findings

### P1 - Runtime memory invariant omits the drainable root register and measures only after `drain()`

**Location:** `tests/unit/html2md/test_memory_invariant.py:20-43`, `src/html2md/emitter.py:80`, `src/html2md/emitter.py:97-105`, `src/html2md/emitter.py:297-305`

**Problem**

`tests/unit/html2md/test_memory_invariant.py::register_footprint` counts `MarkdownEmitter._carry`, `MarkdownEmitter._tail`, `MarkdownEmitter._text_buf`, each `Frame.content`, `Frame.pending_ws`, and table buffers, but it does **not** count `MarkdownEmitter.root`. `MarkdownEmitter.root` is a live string register: `src/html2md/emitter.py:80` stores top-level output committed since the last drain, `src/html2md/emitter.py:97-105` returns it as the active buffer when no buffering ancestor exists, and `src/html2md/emitter.py:297-305` folds and clears it during `MarkdownEmitter.drain`.

The omission matters because `_peak_footprint` also measures only **after** calling `driver.drain()` on each chunk (`tests/unit/html2md/test_memory_invariant.py:38-41`). That means the invariant test does not observe the peak live root register before drain, and it would not catch regressions where completed top-level output accumulates in `MarkdownEmitter.root` instead of being released promptly. In other words, the test proves that open frame/table registers stay bounded after successful drains; it does not prove the claimed streaming resident-memory invariant for all live registers.

This is directly at odds with `docs/design.md:1107-1108`, which lists `root` as the streamed-root DSTT register, and with `docs/design.md:1152-1156`, which says the runtime invariant measures the live register footprint excluding only already-drained output. `MarkdownEmitter.root` before `drain()` is not already-drained output.

**Suggested fix**

Include `sum(len(s) for s in em.root)` in `register_footprint`, and sample the footprint both before and after each `driver.drain()` in `_peak_footprint`. Keep the current post-drain sampling too so the test proves drain releases root output, but add a pre-drain peak measurement so root growth is visible. A small regression-style assertion should fail if `MarkdownEmitter.drain` stops clearing `MarkdownEmitter.root` or if transparent-root output grows with total input rather than the current chunk/open block/table bound.

---

### P2 - The committed runtime invariant is synthetic-only and does not validate the xlarge fixture promised by the bead

**Location:** `tests/unit/html2md/test_memory_invariant.py:46-111`, `docs/design.md:1152-1158`

**Problem**

The bead asks for a runtime/test invariant "validated on xlarge." The committed tests exercise useful synthetic shapes (many small paragraphs, deep nesting, one giant paragraph, a small table, repeated text/span pairs), but none of `tests/unit/html2md/test_memory_invariant.py:46-111` runs against the real benchmark xlarge fixture or any fixture-backed large document.

Synthetic tests are valuable and should stay, but the explicit xlarge validation is absent from the committed harness. Without it, the claim has not been checked against the real-world document shape used elsewhere for the streaming/benchmark story.

**Suggested fix**

Add an on-demand/nightly fixture-backed invariant test (skip-if-absent is fine) that streams `benchmarks/fixtures/xlarge.html` and records the same live-register footprint. If xlarge is too slow for `make test`, put it behind the existing nightly/on-demand convention and document its runner; keep the synthetic unit tests in the fast suite.

## Positive notes

- The formal model in `docs/design.md:1085-1148` is substantially improved: it correctly treats SAX as a nested word, maps the important emitter registers, qualifies the memory bound as `O(open-depth + largest-open-block + table-reservoir)`, and explains why text coalescing is needed for chunk-invariance.
- The synthetic tests do exercise important qualitative cases, including the documented giant-open-block exception and table reservoir locality.

## Tests run

- `uv run pytest tests/unit/html2md/test_memory_invariant.py -vv` → 6 passed in 0.42s
- `uv run ruff check tests/unit/html2md/test_memory_invariant.py` → passed

## Summary

2 findings: 0 P0, 1 P1, 1 P2, 0 P3

**Verdict**: Not approved
