"""SPIKE (throwaway, bead zo-1fp.7) — does a CHUNKED walk+emit keep the asyncio
event loop alive, where the monolithic walk+emit froze it?

Context (from my zo-1fp.4 GIL spike): lxml's C parse releases the GIL, but the
Python-side **tree walk + markdown emit reacquire it** — a monolithic walk pinned
every event-loop heartbeat at ~13 ms (= a pure-Python CPU loop). coder-1's zo-1fp.6
showed the FEED/PARSE side is async-friendly at a 64 KiB chunk (p99 < 0.5 ms). The
make-or-break phase-2 question this spike answers is the OTHER side:

  If we drive the walk+emit incrementally — feed 64 KiB at a time into an
  lxml.etree.HTMLPullParser, emit markdown for the events that completed, and YIELD
  to the loop between chunks (each chunk's feed+emit is its own asyncio.to_thread
  call) — does the heartbeat stay alive (p99 -> ~1 ms), vs the monolithic walk
  (p99 ~13 ms)?

We compare, on the same document and the same heartbeat sampler:

  monolithic   — etree.fromstring(whole doc) + one Python walk+emit, in ONE
                 to_thread call. The GIL-holding baseline (reproduces zo-1fp.4).
  chunked      — HTMLPullParser fed 64 KiB/chunk; each chunk's feed+emit+clear in
                 its own to_thread; the driver awaits between chunks. Cooperative
                 yields = the to_thread boundaries.
  chunked_cemit— same incremental drive, but emit via lxml's C serializer
                 (etree.tostring per completed block) instead of Python string
                 building — sanity-checks the "push emit into C" alternative.

Metrics per variant: heartbeat p50/p95/p99/max (ms), total convert wall (throughput),
and time-to-first-output (TTFO) — when the first markdown fragment was produced.

Run:
    uv run python benchmarks/spikes/chunked_emit_pipeline.py [path_to_html] [feed_kib]
"""

import asyncio
import statistics
import sys
import time
from pathlib import Path

from lxml import etree

INTERVAL = 0.001          # 1ms heartbeat target
DEFAULT_FEED = 64 * 1024  # coder-1's zo-1fp.6 recommended feed size

# Minimal, representative markdown markers — the point is the SHAPE/COST of
# per-node Python emit work (marker lookup + text escape + concat), not a correct
# converter (that's the phase-2 implementation).
_ESCAPE = str.maketrans({"\\": "\\\\", "*": "\\*", "_": "\\_", "`": "\\`",
                         "[": "\\[", "]": "\\]"})
_PREFIX = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### ",
           "li": "- ", "blockquote": "> ", "strong": "**", "b": "**",
           "em": "_", "i": "_", "code": "`"}
_SUFFIX = {"strong": "**", "b": "**", "em": "_", "i": "_", "code": "`",
           "p": "\n\n", "h1": "\n\n", "h2": "\n\n", "h3": "\n\n",
           "h4": "\n\n", "li": "\n", "ul": "\n", "ol": "\n", "blockquote": "\n\n"}


def _emit_fragment(el) -> str:
    tag = el.tag if isinstance(el.tag, str) else None
    if tag is None:
        return ""
    parts = [_PREFIX.get(tag, "")]
    if tag == "a":
        href = el.get("href", "")
        text = (el.text or "").translate(_ESCAPE)
        parts.append(f"[{text}]({href})")
    else:
        if el.text:
            parts.append(el.text.translate(_ESCAPE))
    parts.append(_SUFFIX.get(tag, ""))
    if el.tail:
        parts.append(el.tail.translate(_ESCAPE))
    return "".join(parts)


# ---- incremental (pull-parser) emitter --------------------------------------

class IncrementalEmitter:
    """Feed bytes in chunks; on each completed element emit a markdown fragment and
    clear it (bounded memory — does not retain the whole tree). first_output_perf
    records when the first fragment was produced, for TTFO."""

    def __init__(self, c_emit: bool = False):
        self.parser = etree.HTMLPullParser(events=("end",), huge_tree=True)
        self.parts: list[str] = []
        self.first_output_perf: float | None = None
        self._c_emit = c_emit

    def feed(self, chunk: bytes) -> None:  # runs on a worker thread
        self.parser.feed(chunk)
        self._drain()

    def _drain(self) -> None:
        for _action, el in self.parser.read_events():
            if self._c_emit:
                frag = etree.tostring(el, method="text", encoding="unicode")
            else:
                frag = _emit_fragment(el)
            if frag:
                if self.first_output_perf is None:
                    self.first_output_perf = time.perf_counter()
                self.parts.append(frag)
            el.clear()  # free children → bounded memory while streaming

    def close(self) -> str:
        self.parser.close()
        self._drain()
        return "".join(self.parts)


# ---- target-parser emitter (the design's §4.1 choice) -----------------------

class MarkdownTarget:
    """lxml target-parser callback emitter: start/data/end fire DURING feed(),
    interleaved with the C parse — no DOM is built (O(depth) memory, just the tag
    stack). The contiguous GIL-held span is a single callback, not a whole chunk's
    drain (vs HTMLPullParser). close() returns the joined markdown."""

    def __init__(self):
        self.parts: list[str] = []
        self.first_output_perf: float | None = None
        self._href = ""

    def _append(self, s: str) -> None:
        if self.first_output_perf is None:
            self.first_output_perf = time.perf_counter()
        self.parts.append(s)

    def start(self, tag, attrib):
        if tag == "a":
            self._href = attrib.get("href", "")
            self._append("[")
        else:
            pre = _PREFIX.get(tag)
            if pre:
                self._append(pre)

    def data(self, text):
        if text:
            self._append(text.translate(_ESCAPE))

    def end(self, tag):
        if tag == "a":
            self._append(f"]({self._href})")
        suf = _SUFFIX.get(tag)
        if suf:
            self._append(suf)

    def close(self):
        return "".join(self.parts)


def _make_target_parser() -> tuple:
    target = MarkdownTarget()
    parser = etree.HTMLParser(target=target, huge_tree=True)
    return parser, target


# ---- monolithic baseline ----------------------------------------------------

class _MonoState:
    def __init__(self):
        self.first_output_perf: float | None = None


def monolithic_convert(data: bytes, state: _MonoState) -> str:
    root = etree.fromstring(data, etree.HTMLParser(huge_tree=True))
    parts: list[str] = []
    for el in root.iter():
        frag = _emit_fragment(el)
        if frag:
            if state.first_output_perf is None:
                state.first_output_perf = time.perf_counter()
            parts.append(frag)
    return "".join(parts)


# ---- heartbeat-sampled runners ----------------------------------------------

MISS_MS = 2.0  # a heartbeat later than this is a "missed beat" (async-yield SLO)


def _summary(name: str, jitter: list[float], total_s: float, ttfo_ms: float | None,
             out_bytes: int) -> dict:
    s = sorted(jitter)

    def pct(q: float) -> float:
        return s[min(len(s) - 1, int(q * len(s)))] if s else float("nan")

    missed = sum(1 for v in jitter if v > MISS_MS)
    return {
        "variant": name, "n": len(s), "total_s": total_s, "ttfo_ms": ttfo_ms,
        "out_mb": out_bytes / 1024 / 1024,
        "p50": pct(.50), "p95": pct(.95), "p99": pct(.99),
        "max": max(s) if s else float("nan"),
        "mean": statistics.mean(s) if s else float("nan"),
        # missed-beat count + total stall time are robust to the count-bias that
        # makes percentiles understate GIL-held windows (fewer beats fire while the
        # GIL is held, so they're under-weighted in percentiles).
        "missed": missed,
        "miss_pct": 100.0 * missed / len(s) if s else float("nan"),
        "stall_ms": sum(v for v in jitter if v > 0),
    }


async def _sample(done: asyncio.Event, jitter: list[float]) -> None:
    while not done.is_set():
        t0 = time.perf_counter()
        await asyncio.sleep(INTERVAL)
        jitter.append((time.perf_counter() - t0 - INTERVAL) * 1000.0)


async def run_chunked(data: bytes, feed_size: int, c_emit: bool = False) -> dict:
    em = IncrementalEmitter(c_emit=c_emit)
    jitter: list[float] = []
    done = asyncio.Event()
    sampler = asyncio.create_task(_sample(done, jitter))
    t0 = time.perf_counter()
    for i in range(0, len(data), feed_size):
        # each chunk's feed+emit holds the GIL only for that chunk; the await
        # boundary lets the loop (and the heartbeat sampler) run between chunks.
        await asyncio.to_thread(em.feed, data[i:i + feed_size])
    md = await asyncio.to_thread(em.close)
    total = time.perf_counter() - t0
    done.set()
    await sampler
    ttfo = (em.first_output_perf - t0) * 1000.0 if em.first_output_perf else None
    name = "chunked_cemit" if c_emit else "chunked"
    return _summary(name, jitter, total, ttfo, len(md.encode()))


async def run_target_chunked(data: bytes, feed_size: int) -> dict:
    """Target parser (design §4.1), fed feed_size/chunk, await between chunks —
    apples-to-apples vs the pull-parser 'chunked' variant."""
    parser, target = _make_target_parser()
    jitter: list[float] = []
    done = asyncio.Event()
    sampler = asyncio.create_task(_sample(done, jitter))
    t0 = time.perf_counter()
    for i in range(0, len(data), feed_size):
        await asyncio.to_thread(parser.feed, data[i:i + feed_size])
    md = await asyncio.to_thread(parser.close)
    total = time.perf_counter() - t0
    done.set()
    await sampler
    ttfo = (target.first_output_perf - t0) * 1000.0 if target.first_output_perf else None
    return _summary("target_chunked", jitter, total, ttfo, len(md.encode()))


async def run_target_single_feed(data: bytes) -> dict:
    """Target parser, WHOLE doc in ONE feed() call on a worker thread (no chunking).
    Discriminating test: if the heartbeat stays alive here, lxml releases the GIL
    BETWEEN target callbacks mid-feed() (→ larger feed chunks justified). If it's
    pinned ~13ms like the monolithic walk, it does NOT (→ chunking is mandatory)."""
    parser, target = _make_target_parser()

    def run_whole():
        parser.feed(data)
        return parser.close()

    jitter: list[float] = []
    done = asyncio.Event()
    sampler = asyncio.create_task(_sample(done, jitter))
    t0 = time.perf_counter()
    md = await asyncio.to_thread(run_whole)
    total = time.perf_counter() - t0
    done.set()
    await sampler
    ttfo = (target.first_output_perf - t0) * 1000.0 if target.first_output_perf else None
    return _summary("target_1feed", jitter, total, ttfo, len(md.encode()))


async def run_monolithic(data: bytes) -> dict:
    state = _MonoState()
    jitter: list[float] = []
    done = asyncio.Event()
    sampler = asyncio.create_task(_sample(done, jitter))
    t0 = time.perf_counter()
    md = await asyncio.to_thread(monolithic_convert, data, state)
    total = time.perf_counter() - t0
    done.set()
    await sampler
    ttfo = (state.first_output_perf - t0) * 1000.0 if state.first_output_perf else None
    return _summary("monolithic", jitter, total, ttfo, len(md.encode()))


def fmt(r: dict) -> str:
    ttfo = f"{r['ttfo_ms']:7.1f}" if r["ttfo_ms"] is not None else "    -  "
    return (f"{r['variant']:<14} total={r['total_s']:6.3f}s ttfo={ttfo}ms "
            f"out={r['out_mb']:5.1f}MB  p50={r['p50']:6.3f} p95={r['p95']:6.3f} "
            f"p99={r['p99']:7.3f} max={r['max']:8.3f}ms  "
            f"missed>{MISS_MS:g}ms={r['missed']:>4}/{r['n']:<4}({r['miss_pct']:4.1f}%) "
            f"stall={r['stall_ms']:7.1f}ms")


async def main() -> None:
    here = Path(__file__).parent
    default = next((p for p in (here / "sample_50mb.html", here / "sample_5mb.html")
                    if p.exists()), here / "sample_5mb.html")
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    feed = int(sys.argv[2]) * 1024 if len(sys.argv) > 2 else DEFAULT_FEED
    if not path.exists():
        sys.exit(f"missing {path}; run gen_sample_html.py first")
    data = path.read_bytes()

    # warm imports/JIT on a small slice
    _ = monolithic_convert(data[:100_000], _MonoState())

    print(f"python {sys.version.split()[0]} | GIL switch {sys.getswitchinterval()*1000:.0f}ms"
          f" | {len(data)/1024/1024:.1f}MB ({path.name}) | feed {feed//1024}KiB"
          f" | heartbeat {INTERVAL*1000:.0f}ms\n")

    results = [
        await run_monolithic(data),
        await run_chunked(data, feed),
        await run_chunked(data, feed, c_emit=True),
        await run_target_chunked(data, feed),
        await run_target_single_feed(data),
    ]
    print("Heartbeat jitter + throughput + time-to-first-output:\n")
    for r in results:
        print("  " + fmt(r))

    mono, chunk = results[0], results[1]
    keeps_alive = chunk["p99"] < 0.25 * mono["p99"]
    print("\nVerdict:")
    print(f"  monolithic walk+emit: p99 {mono['p99']:.2f}ms, "
          f"{mono['missed']}/{mono['n']} beats missed (>{MISS_MS:g}ms), "
          f"{mono['stall_ms']:.0f}ms total stall — GIL held through the walk.")
    print(f"  chunked  walk+emit:   p99 {chunk['p99']:.2f}ms, "
          f"{chunk['missed']}/{chunk['n']} missed, {chunk['stall_ms']:.0f}ms stall, "
          f"ttfo {chunk['ttfo_ms']:.1f}ms.")
    print(f"  => chunking the walk+emit with awaits "
          f"{'KEEPS THE LOOP ALIVE' if keeps_alive else 'did NOT help'}: "
          f"p99 {mono['p99']:.1f} -> {chunk['p99']:.1f}ms ({mono['p99']/chunk['p99']:.0f}x lower), "
          f"max {mono['max']:.0f} -> {chunk['max']:.0f}ms, "
          f"missed {mono['miss_pct']:.0f}% -> {chunk['miss_pct']:.0f}%.")
    print(f"     (NB: TOTAL GIL work is ~unchanged — {mono['stall_ms']:.0f} vs "
          f"{chunk['stall_ms']:.0f}ms stall; chunking BOUNDS each stall into <{MISS_MS:g}ms "
          f"slices, it doesn't remove the work.)")
    print(f"  cost: {chunk['total_s']/mono['total_s']:.2f}x wall vs monolithic; "
          f"first output {chunk['ttfo_ms']:.0f}ms vs {mono['ttfo_ms']:.0f}ms (whole-doc) "
          f"= {mono['ttfo_ms']/chunk['ttfo_ms']:.0f}x faster TTFO.")
    cem = results[2]
    print(f"  C-emit variant: total GIL stall {cem['stall_ms']:.0f}ms "
          f"({mono['stall_ms']/cem['stall_ms']:.1f}x less than Python emit) and "
          f"{cem['total_s']/mono['total_s']:.2f}x wall — 'push emit into C' is the lever "
          f"that cuts TOTAL GIL work, chunking is the lever that bounds per-stall latency.")

    tchunk, t1feed = results[3], results[4]
    print("\nTarget parser (design §4.1) confirmation:")
    print(f"  target_chunked (feed/chunk + await between): p99 {tchunk['p99']:.2f}ms, "
          f"missed {tchunk['miss_pct']:.1f}%, ttfo {tchunk['ttfo_ms']:.1f}ms — "
          f"{'<=' if tchunk['p99'] <= chunk['p99'] else '>'} pull-parser p99 {chunk['p99']:.2f}ms.")
    feeds_alive = t1feed["miss_pct"] < 5.0 and t1feed["p99"] < 0.5 * mono["p99"]
    print(f"  target_1feed (WHOLE doc in ONE feed, no chunking): p99 {t1feed['p99']:.2f}ms, "
          f"missed {t1feed['miss_pct']:.1f}%, max {t1feed['max']:.0f}ms.")
    print(f"  => mid-feed GIL release between callbacks: "
          f"{'YES' if feeds_alive else 'NO'} — "
          + ("the loop stays alive even with the whole doc in one feed(), so lxml "
             "releases the GIL between target callbacks; the feed-chunk default could "
             "be relaxed (responsiveness comes from libxml2, not just our chunking)."
             if feeds_alive else
             "one big feed() pins the loop like the monolithic walk, so chunking the "
             "FEED is mandatory for responsiveness — keep the 64KiB feed default."))


if __name__ == "__main__":
    asyncio.run(main())
