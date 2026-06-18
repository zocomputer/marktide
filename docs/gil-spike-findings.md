# GIL-release spike findings (bead zo-1fp.4)

Date: 2026-06-17 · Owner: misc-leaf · Status: **done**
Code: `benchmarks/spikes/gil_probe.py` (+ `gen_sample_html.py`). Throwaway spike —
the production benchmark harness is coder-3-leaf's `zo-1fp.2`. Reusable heartbeat
sampler shared in `benchmarks/spikes/heartbeat_snippet.md`.

## Question

The project premise is "lxml's C parser releases the GIL, so a parse on a worker
thread won't stall the asyncio event loop." That premise is true but **incomplete**.
The decision that shapes phase-2's threading design (reviewer-leaf rubric pt 7) is:
does the **whole conversion pipeline** — parse → tree walk → markdown emit — stay
async-friendly, or only the parse? lxml's C parse releases the GIL, but **Python-side
tree walking and markdown emission reacquire it.**

## Method

Main thread runs a tight asyncio loop of 1 ms `await asyncio.sleep`. We measure
`actual_elapsed - 1ms` = **heartbeat jitter** (event-loop scheduling latency). While
that loop runs, a worker thread runs **one stage** of the pipeline, single-shot. Low
jitter ⇒ the worker yields the GIL (loop stays responsive); jitter pinned near the
5 ms GIL switch interval on *every* sample ⇒ the worker holds the GIL.

Walk/emit operate on a pre-parsed tree so each stage is measured in isolation. Sample:
50 MB single well-formed synthetic HTML doc, CPython 3.12.13 (standard GIL build,
`Py_GIL_DISABLED` unset), 5 ms switch interval. Each stage single-shot.

## Results (representative run, heartbeat jitter in ms)

| workload      | what                          | work    | n    | p50   | p95   | p99    | max     |
|---------------|-------------------------------|---------|------|-------|-------|--------|---------|
| idle          | sampling loop alone (floor)   | —       | 1182 | 0.28  | 0.31  | 0.33   | 8.4     |
| **lxml_parse**| stage (a) — C parse           | 0.50 s  | 316  | **0.27** | **0.29** | **0.33** | 101.2¹ |
| tree_walk     | stage (b) — Python tree walk  | 0.21 s  | 14   | 13.8  | 15.4  | 15.4   | 15.4    |
| md_emit       | stage (c) — Python md emit    | 1.00 s  | 68   | 13.5  | 15.3  | 33.9   | 33.9    |
| bs4           | BeautifulSoup(html.parser)    | 13.1 s  | 743  | 13.5  | 15.4  | 113.4  | 506.9   |
| markdownify   | the library we replace        | 24.3 s  | 1496 | 13.5  | 15.3  | 15.9   | 1117.8  |
| pyloop        | pure-Python CPU (control)     | 0.42 s  | 29   | 13.9  | 15.3  | 17.2   | 17.2    |
| direct        | parse run ON the loop (neg.)  | 0.45 s  | 78   | 0.28  | 435.3 | 514.9  | 514.9   |

¹ `lxml_parse`'s lone `max` spike is the **single** ElementTree-construction boundary
(one ~100 ms Python-side event when the C parse hands back the tree object). Every
other one of the 316 heartbeats during the 0.5 s parse ran at idle latency.

## Findings

1. **lxml's C parse releases the GIL — confirmed, decisively.** During a single 0.5 s
   parse, all 316 event-loop heartbeats ran at idle latency (p50/p95/p99 =
   0.27/0.29/0.33 ms, identical to the 0.28/0.31/0.33 ms floor). The parse is fully
   concurrent with the asyncio loop. The only GIL-holding moment is one ~100 ms
   ElementTree-construction blip at the boundary.

2. **The Python-side stages HOLD the GIL — the load-bearing finding.** `tree_walk`
   and `md_emit` pin **every** heartbeat at ~13–14 ms, indistinguishable from the
   pure-Python CPU control (`pyloop`). Walking an lxml tree from Python and building
   markdown strings is ordinary Python bytecode; it does not yield.

   > **Offloading the parse alone is necessary but NOT sufficient.** A worker thread
   > that parses (GIL released) and then walks/emits in Python stalls the loop for the
   > walk+emit duration — on this 50 MB sample, emit (~1.0 s) is *longer* than the
   > parse (~0.5 s).

3. **Negative control quantifies the cost of not offloading.** Running the parse
   directly on the loop thread (`direct`) freezes the heartbeat for the full parse
   (p95 = 435 ms, max = 515 ms).

4. **markdownify/bs4 (the incumbent) are GIL-bound throughout AND ~25–50× slower**
   than lxml on the same 50 MB input (markdownify 24.3 s, bs4 13.1 s vs lxml parse
   0.5 s) — exactly the problem statement.

5. **Large-doc gotcha for the design:** libxml2 silently **truncates** documents past
   its internal guards. A 50 MB doc parsed in ~35 ms (a fraction of the tree) until I
   set `etree.HTMLParser(huge_tree=True)`. Real large inputs need `huge_tree=True`
   (with the usual caution that it lifts billion-laughs/entity-expansion protections —
   pair it with input-size limits). Also note `benchmarks/fixtures/*.html` are
   *repeated full HTML documents*, so libxml2 stops at the first `</html>` — they
   under-measure single-parse timing; use a single well-formed doc.

## Implication for phase-2 design (→ coder-2-leaf)

Releasing the GIL during parse is real and worth building on, but the threading design
must keep the **whole** pipeline async-friendly:

- **Chunk the walk+emit and `await` between chunks** — drive an incremental
  `iterparse`/SAX-style walk that returns control to the loop every N nodes/bytes,
  rather than one blocking tree walk. This is the README's streaming model and is the
  recommended path.
- **Or push the hot walk+emit into C** (a Cython/C emitter, or lxml-native
  serialization) so the heavy stage releases the GIL like the parse does.
- The heartbeat-jitter percentile method is validated as the **async-yield acceptance
  metric** for the design and the production harness: assert the converter's worker,
  end to end, keeps main-loop p99 heartbeat jitter within a small multiple of idle
  (e.g. < 2 ms), not just during parse but across walk+emit.

## Reproduce

```bash
uv run python benchmarks/spikes/gen_sample_html.py 50 benchmarks/spikes/sample_50mb.html
uv run python benchmarks/spikes/gil_probe.py            # defaults to the 50MB doc
uv run python benchmarks/spikes/gil_probe.py path/to/your.html
```

Canonical output captured in `benchmarks/spikes/gil_probe_output.txt`.
