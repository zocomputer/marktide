# v2 performance profile — findings (zo-q2m.1)

Profile-first, no converter changes. Harness: `benchmarks/spikes/perf_profile.py`
(raw output: `benchmarks/spikes/perf_profile_output.txt`). Sample: a **single
well-formed 50 MiB** document (`sample_50mb.html`, 4 663 articles). The repeated-doc
`xlarge` fixture is unsuitable for this — lxml truncates it at the first `</html>`, so
it would under-measure. Times are best-of-3, CPython 3.12.

## TL;DR

- **The Python emission is the entire bottleneck.** The lxml parse floor is **~90
  MiB/s**; full `marktide.convert` is **~8.6 MiB/s**. Emission is **90 % of convert
  wall-time**; parse is ~10 %. Parser tuning is **not** a lever.
- **It's death by a million callbacks**, not one hot loop. The 50 MiB sample fires
  **6.1 M Python callbacks** (1.76 M `start`, 1.76 M `end`, 2.59 M `data`). Cost is
  spread across per-element dispatch, regex text processing, an O(depth) ancestor scan,
  and the boundary-collapse fold — each cheap per call, but called millions of times.
- **Streaming is free.** `convert_stream` (64 KiB) is within **+0 %** of one-shot
  `convert` — ChunkPump/drain overhead is negligible. Not a target.

## Throughput by stage (50 MiB single doc)

| stage | time | throughput | note |
|---|---|---|---|
| parse + no-op target (FLOOR) | 0.55 s | **90.1 MiB/s** | pure libxml2 parse + empty Python callbacks |
| parse + counting target | 0.60 s | 83.9 MiB/s | + trivial per-callback Python work |
| lxml_naive (parse + Python tree walk) | 0.83 s | 60.6 MiB/s | parse + a plain recursive walk, no Markdown |
| **marktide.convert (one-shot)** | **5.80 s** | **8.6 MiB/s** | the system under test |
| marktide.convert_stream (64 KiB) | 5.83 s | 8.6 MiB/s | +0 % vs one-shot |

**Emission overhead = convert − floor = 5.25 s = 90 % of convert.** The gap to lxml_naive
(60 MiB/s) is the cost of real Markdown semantics (escaping, whitespace, collapse,
sibling trim, dispatch) over a bare walk.

## Ranked hotspots (cProfile `tottime`, convert() only)

Profiler inflates wall-time ~4× (23.6 s profiled); the **relative** shares hold. Grouped
by what the work actually is (builtins re-attributed to their caller):

| rank | hotspot | ~tottime | what it is |
|---|---|---|---|
| 1 | **Per-element dispatch** (`start` 2.26s + `end` 1.42s + `state.push` 0.49s + `_buf` 0.41s + `dict.get` 0.35s) | **~5.4 s** | every one of 1.76 M elements: push/pop a Frame, look up the handler, set the buffering flag, run sibling-whitespace bookkeeping, call the handler. The single biggest cost. |
| 2 | **Boundary-collapse fold** (`_collapse_join` 1.28s + `_split_newlines` 0.81s + its genexpr 0.69s + `re.match` 0.48s + `re.Match.group` 0.56s) | **~3.8 s** | `_collapse_join` runs per element `end`; `_split_newlines` regex-matches **every** child string (8.8 M `.group` calls). |
| 3 | **Regex text processing** (`re.sub` 1.32s [4.9 M calls] + `str.replace` 0.34s) | **~1.7 s** | `emit_text` runs 2 whitespace `re.sub`s per text node (2.59 M nodes) + escape `replace`s. |
| 4 | **`_in_noformat` ancestor scan** (`any()` 1.14s + `_in_noformat` 0.36s) | **~1.5 s** | called per text node; **scans the whole open-element stack every time** (O(depth) × 2.3 M). |
| 5 | **Output buffering** (`list.append` 0.89s [16.5 M calls] + `str.join` 0.38s) | **~1.3 s** | inherent fragment buffering. |

(`escape` itself is only ~3.5 %; `parser.feed` Python-side dispatch ~1.25 s is the
irreducible C→Python boundary.)

## Ranked optimization ideas (confirmed / refuted against the data)

### Tier 1 — cheap Python wins, no rewrite (do first)

1. **`_in_noformat` → O(1) depth counter** — *confirmed, ~6 % (1.5 s).* Replace the
   per-text-node `any(frame.tag in {pre,code,kbd,samp} for frame in stack)` stack scan
   with a `noformat_depth` counter incremented/decremented at start/end (exactly like
   the existing `pre_depth`). Turns O(depth)×2.3 M into O(1). Trivial, safe.
2. **`_buf()` → cached buffering-target pointer** — *confirmed, ~0.4 s + removes an
   O(depth) scan.* `_buf` is called 3.7 M times and walks the stack to find the nearest
   buffering frame. Maintain the current target on push/pop instead of re-scanning.
3. **Fast-path `_split_newlines` / `_collapse_join`** — *confirmed, targets ~3.8 s.*
   Most child strings have **no** leading/trailing newline (inline content). Guard the
   regex with a cheap `if not (s.startswith("\n") or s.endswith("\n"))` fast-path that
   returns `("", s, "")` without the `re.match`+3×`.group`. Skips the regex for the
   majority of 8.8 M calls.
4. **Fast-path whitespace normalization in `emit_text`** — *confirmed, targets ~1.7 s.*
   Skip the two `re.sub`s when the text has no collapsible run (no `\t`/`\n`/double
   space). A single `str` scan or membership check is far cheaper than two regex subs on
   each of 2.59 M nodes.

### Tier 2 — structural

5. **C/Cython emitter for the hot callback path** — *confirmed, the biggest lever (≈90 %
   of time is here).* The cost is fundamentally 6.1 M Python callbacks each doing small
   work. Moving `start`/`end`/`data` + dispatch + buffering into Cython (or a C target)
   attacks the dominant cost directly; the zo-1fp.7 spike already showed a C-serializer
   path cut total GIL stall ~4× and beat the monolithic walk. Highest ceiling, highest
   effort — pursue after Tier 1 quantifies how far pure-Python tuning gets.
6. **Reduce per-`start` allocation** — *confirmed, part of hotspot 1.* `dict(attrs)` is
   copied for every element even when the handler never reads attrs; defer/avoid the copy
   (most elements are blocks/inline with no attr use). Fewer Frame field initialisations.

### Tier 3 — minor / refuted

7. **`str.translate` for escaping** — *partial, low priority (~3.5 %).* Could fold the
   asterisk/underscore `replace`s + misc regex into one `translate`, but escape is a
   small slice; not worth it until Tier 1/2 land.
8. **lxml parser tuning** — *refuted.* Parse is ~10 % of convert (floor is 90 MiB/s);
   tuning the parser cannot move the 90 % that is emission.
9. **Streaming / ChunkPump overhead** — *refuted.* `convert_stream` is +0 % vs
   `convert`; the drain/coalescing path adds no measurable cost.
10. **Output buffering rework (bytearray/pre-size)** — *refuted as a primary target.*
    `list.append` is 16.5 M calls but only ~0.9 s and is inherent to fragment assembly;
    Python-level buffer tricks won't materially help without the Cython rewrite (5).

## Recommended sequence

Tier 1 (1→4) first — they are small, safe, independently testable, and the profile says
they reclaim a large share of emission time with no architecture change; re-profile after
each to confirm. Then decide on the Cython emitter (5) with Tier-1-adjusted numbers as the
new baseline. Do **not** touch the parser or streaming path.
