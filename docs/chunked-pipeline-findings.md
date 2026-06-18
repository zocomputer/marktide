# Chunked async-pipeline prototype findings (bead zo-1fp.7)

Date: 2026-06-17 · Owner: misc-leaf · Status: **done**
Code: `benchmarks/spikes/chunked_emit_pipeline.py`. Throwaway spike. Builds directly
on the GIL spike [`docs/gil-spike-findings.md`](gil-spike-findings.md) (zo-1fp.4) and
uses coder-1's 64 KiB feed size from the parse-side sweep (zo-1fp.6).

## The make-or-break question

zo-1fp.4 proved lxml's C parse releases the GIL but the **Python walk + markdown
emit reacquire it** — a monolithic walk pinned every event-loop heartbeat at ~13 ms.
coder-1's zo-1fp.6 proved the FEED/PARSE side is async-friendly at 64 KiB. This spike
answers the remaining phase-2 architecture unknown:

> Does driving the walk+emit **incrementally** — feed 64 KiB at a time into an
> `lxml.etree.HTMLPullParser`, emit markdown for the completed elements, and **yield
> to the loop between chunks** (each chunk's feed+emit is its own `asyncio.to_thread`
> call) — keep the event loop alive, where the monolithic walk froze it?

**Answer: yes, decisively.**

## Method

Same heartbeat sampler as zo-1fp.4 (main thread runs a 1 ms `asyncio.sleep` loop;
jitter = actual − target). Three variants convert the same document while sampled:

- **monolithic** — `etree.fromstring(whole doc)` + one Python walk+emit, in ONE
  `to_thread`. The GIL-holding baseline.
- **chunked** — `HTMLPullParser` fed 64 KiB/chunk; each chunk's feed + Python emit +
  `el.clear()` runs in its own `to_thread`, the driver `await`s between chunks.
  Cooperative yields = the `to_thread` boundaries. Bounded memory (`el.clear()`).
- **chunked_cemit** — same incremental drive, emit via lxml's C serializer
  (`etree.tostring(el, method="text")`) instead of Python string building —
  sanity-checks the "push emit into C" alternative.

Metrics: heartbeat p50/p95/p99/max; **missed beats** (heartbeats later than 2 ms —
the async-yield SLO, robust to the count-bias below); total convert wall
(throughput); and **time-to-first-output (TTFO)**.

> Measurement note: percentiles-by-count *understate* GIL-held windows — while the
> GIL is held the sampler itself can't wake, so fewer (delayed) beats are recorded
> and they're under-weighted. That's why monolithic's p50 looks idle-like (0.27 ms)
> while 20 % of its beats are missed. **Missed-beat % and max are the honest "is the
> loop alive" signals**; p99 corroborates.

## Results (50 MB single well-formed doc, CPython 3.12, 64 KiB feed)

| variant       | total  | TTFO    | p99     | max      | missed >2 ms | total stall |
|---------------|--------|---------|---------|----------|--------------|-------------|
| monolithic    | 1.61 s | 378 ms  | 15.4 ms | 110 ms   | **20 %** (77/378) | 1237 ms |
| **chunked**   | 1.90 s | **1.7 ms** | **2.4 ms** | **11 ms** | **1 %** (11/812) | 1091 ms |
| chunked_cemit | 1.24 s | 1.0 ms  | 1.6 ms  | 15 ms    | 1 % (9/932)  | **309 ms** |

(5 MB results are consistent: monolithic p99 15.3 ms / 19 % missed / TTFO 42 ms vs
chunked p99 1.8 ms / 0 % missed / TTFO 1.4 ms.)

## Findings

1. **Chunking the walk+emit with awaits keeps the loop alive — the core phase-2
   assumption holds.** Missed beats drop from **20 % → 1 %**, p99 from **15.4 → 2.4 ms**
   (6–9×), worst-case stall from **110 → 11 ms**. The loop stays responsive throughout
   a multi-second conversion.

2. **Throughput cost is small: ~1.18× wall** vs monolithic (the `to_thread`-per-chunk
   dispatch overhead). Acceptable for the async-friendliness it buys.

3. **TTFO collapses ~220×: 378 ms → 1.7 ms.** Streaming emits the first markdown
   almost immediately instead of after the whole document is walked — a major UX win
   for the streaming API in the README, independent of the GIL story.

4. **Chunking BOUNDS per-stall latency; it does not reduce TOTAL GIL work.** Total
   stall is ~unchanged (1237 → 1091 ms) — the same emit work happens, just sliced into
   <2 ms pieces so no single stall blocks the loop. This is the key mental model for
   the design: *chunk size sets the worst-case heartbeat stall; it does not make the
   conversion cheaper.*

5. **The lever that cuts total GIL work is moving emit into C.** `chunked_cemit` cut
   total stall **4× (1237 → 309 ms)** AND ran faster than monolithic (0.77× wall),
   because the per-node Python string-building is the dominant remaining GIL cost. So
   the two levers are orthogonal and complementary:
   - **chunk size** → bounds per-stall heartbeat latency (responsiveness).
   - **emit in C/Cython** → reduces total GIL-held time (less contention overall,
     higher throughput).

## Target-parser confirmation (design §4.1 — the chosen API)

The above used `HTMLPullParser` (which builds a tree; I called `el.clear()` to bound
memory). The design picks the **target parser** (`etree.HTMLParser(target=...)`):
callback-based, no DOM, O(depth) memory. Two variants added to confirm the result
carries to the real API, and to answer "does lxml release the GIL *between* target
callbacks mid-`feed()`?" (50 MB, 64 KiB feed; numbers stable across runs):

| variant            | total  | TTFO   | p99      | max    | missed >2 ms | total stall |
|--------------------|--------|--------|----------|--------|--------------|-------------|
| pull-parser chunked| 1.90 s | 1.6 ms | 2.5 ms   | 11 ms  | 1.4 %        | 1083 ms     |
| **target_chunked** | 1.51 s | **0.1 ms** | **0.49 ms** | 18 ms | **0.1 %** | 313 ms |
| **target_1feed**¹  | 1.46 s | 3.0 ms | **0.53 ms** | 20 ms | **0.1 %** | 388 ms |

¹ `target_1feed` = the **whole 50 MB doc in ONE `feed()` call**, zero chunking.

**Findings:**

6. **The target parser is strictly better than the pull-parser on every axis** —
   p99 0.49 ms vs 2.5 ms, TTFO 0.1 ms vs 1.6 ms, total stall 313 ms vs 1083 ms (3.5×
   less GIL work, because it builds no DOM), and faster wall than monolithic. So the
   pull-parser numbers in §4.2 are a **genuine conservative lower bound** — the chosen
   API beats them ~5× on p99.

7. **lxml releases the GIL between target callbacks mid-`feed()` — confirmed (YES).**
   The whole 50 MB doc in a *single* `feed()` (no chunking at all) still keeps the loop
   alive: p99 0.53 ms, 0.1 % missed beats. If the GIL were held continuously, the 5 ms
   involuntary switch interval alone would put p99 in the ~5–13 ms range (as monolithic
   shows). Sub-millisecond p99 is only possible if `feed()` *voluntarily* releases the
   GIL many times — around the C tokenization between each Python callback. This matches
   lxml's documented "releases the GIL during parsing" behavior, with the target
   reacquiring it for each brief callback.

   > **Consequence: feed-chunk size is NOT the responsiveness knob for the target
   > parser.** Responsiveness is intrinsic (libxml2's fine-grained GIL release at
   > element granularity, far finer than 64 KiB). Chunking the feed is for **TTFO
   > cadence, memory/backpressure, and cancellation points** — not heartbeat jitter.
   > The criterion-2 p99 ≤ 2 ms gate is met with ~4× margin even with NO chunking.

8. **Caveat — the ~18–21 ms `max` spikes** (1 beat per ~1000) are an artifact of this
   prototype accumulating all output in a list and `"".join`-ing 30 MB at `close()`
   (one big allocation/GC). The real streaming emitter **flushes output incrementally**
   instead of accumulating, which removes that end-of-parse spike. Worth a regression
   check that sustained conversion holds `max` under the gate.

## Implications for phase-2 design (→ coder-2-leaf)

- **The threading architecture is validated:** incremental target-parser `feed` +
  callback emit, driven via `to_thread`, is async-safe. The monolithic "parse whole
  doc then walk the DOM" is ruled out — it freezes the loop.
- **With the target parser, the responsiveness SLO is essentially FREE** (finding 7):
  libxml2 releases the GIL between callbacks, so even an unchunked `feed()` holds p99
  at ~0.5 ms. So feed-chunk size is **not** the responsiveness knob — tune it for
  **TTFO cadence / memory / cancellation** instead. (This relaxes the responsiveness
  constraint coder-2 hoped to relax: larger feed chunks are fine for jitter; the limit
  is memory/backpressure, not heartbeat.)
- **The remaining lever is throughput, not responsiveness:** a C/Cython emitter cuts
  total GIL work ~4× (findings 5–6). Pure-Python callback emit already passes the 2 ms
  gate with margin, so C emit is an optimization, not a correctness requirement.
- **Flush output incrementally, don't accumulate** (finding 8) — accumulating the full
  output string reintroduces a large end-of-parse GC/alloc spike.
- **Recommend the async-yield acceptance gate be missed-beat % (and max), not just
  p99** — percentiles under-weight GIL-held windows. Suggested gate: **< ~2 % beats
  later than 2 ms, max < ~15 ms**, measured across the FULL convert.
- **`el.clear()` after emit gives bounded memory** while streaming (don't retain the
  whole 30 MB output tree). The full memory-bounding pattern (also drop preceding
  siblings) is an implementation detail for the parser spec.
- A `chunk_size` sweep for walk+emit specifically (TTFO vs jitter vs throughput curve)
  is the natural next quantification if coder-2 wants numeric gates — flagged but not
  run here (zo-1fp.6 covered the parse side; this confirmed the emit side qualitatively).

## Reproduce

```bash
uv run python benchmarks/spikes/chunked_emit_pipeline.py [path.html] [feed_kib]
# defaults to sample_50mb.html @ 64 KiB feed
```

Canonical output: `benchmarks/spikes/chunked_emit_output.txt`.
