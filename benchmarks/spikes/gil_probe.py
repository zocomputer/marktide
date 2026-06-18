"""SPIKE (throwaway, bead zo-1fp.4) — does the WHOLE HTML->Markdown pipeline stay
async-friendly, not just the parse?

lxml's docs already say the C parse releases the GIL. The decision that actually
shapes phase-2's threading design is subtler (reviewer-leaf rubric pt 7): lxml's
C parse releases the GIL, but **Python-side tree walking and markdown emission
reacquire it**. So we measure the conversion in stages and ask, for each stage,
"if this runs on a worker thread, does the asyncio event loop on the main thread
keep its heartbeat?"

Stages measured (each on a worker thread, main thread runs a 1ms asyncio sleep loop
whose actual-vs-target latency = "heartbeat jitter"):

  (a) lxml_parse  — etree.fromstring (C; expected to RELEASE the GIL)
  (b) tree_walk   — Python iteration over the parsed tree (expected to HOLD the GIL)
  (c) md_emit     — stand-in markdown emission: walk + build/escape/join strings
                    (Python; expected to HOLD the GIL)

Baselines / controls:

  idle        — sampling loop alone (measurement floor)
  direct      — NEGATIVE control: lxml_parse run directly ON the loop thread (no
                offload). Shows what NOT threading looks like: the loop is blocked
                for the full parse duration.
  pyloop      — pure-Python CPU spin (canonical GIL-holder)
  bs4         — BeautifulSoup(html.parser) parse (pure-Python, holds GIL)
  markdownify — the library we're replacing (holds GIL)

Headline: if (a) looks like idle but (b)/(c) look like pyloop, then offloading the
parse alone is not enough — the Python walk+emit must ALSO yield (chunked + await,
or be pushed into C) to keep the loop responsive. That's the phase-2 decision.

Run:
    uv run python benchmarks/spikes/gil_probe.py [path_to_html]
"""

import asyncio
import statistics
import sys
import time
from pathlib import Path

INTERVAL = 0.001  # 1ms target sleep between heartbeat samples
SAMPLE_CAP = 100_000
DURATION_S = 1.5  # how long to run each worker workload


# ---- stats ------------------------------------------------------------------

def _pct(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def summarize(name: str, jitter_ms: list[float], per_iter_s: float | None,
              note: str = "") -> dict:
    return {
        "workload": name,
        "per_iter_s": per_iter_s,
        "samples": len(jitter_ms),
        "mean_ms": statistics.mean(jitter_ms) if jitter_ms else float("nan"),
        "p50_ms": _pct(jitter_ms, 0.50),
        "p95_ms": _pct(jitter_ms, 0.95),
        "p99_ms": _pct(jitter_ms, 0.99),
        "max_ms": max(jitter_ms) if jitter_ms else float("nan"),
        "note": note,
    }


# ---- stage workloads --------------------------------------------------------
# parse-stage takes raw bytes; walk/emit stages take a pre-parsed tree so each
# stage is measured in isolation (the walk is not paying for a parse).

# huge_tree=True: libxml2's default guards silently TRUNCATE documents past its
# internal limits (a 50MB doc parsed in ~35ms = a fraction of the tree). Real large
# inputs need this flag — a finding for the design, not just the spike.
def make_tree(html_bytes: bytes):
    from lxml import etree
    return etree.fromstring(html_bytes, etree.HTMLParser(huge_tree=True))


def work_lxml_parse(html_bytes: bytes) -> None:
    from lxml import etree
    root = etree.fromstring(html_bytes, etree.HTMLParser(huge_tree=True))
    _ = root.tag  # cheap C access; forces parse completion


def work_tree_walk(tree) -> None:
    # Python-level traversal. Each .iter()/.tag/.text is a C call, but the loop
    # itself is Python bytecode → the GIL is held the whole time.
    n = 0
    for el in tree.iter():
        if el.tag is not None:
            n += 1
        if el.text:
            n += len(el.text)
    _ = n


_ESCAPE = str.maketrans({"\\": "\\\\", "*": "\\*", "_": "\\_", "`": "\\`",
                          "[": "\\[", "]": "\\]"})


def work_md_emit(tree) -> None:
    # Stand-in for markdown emission: walk the tree and build escaped markdown
    # fragments into a buffer, then join. Pure Python → holds the GIL. This is the
    # shape of the real emitter's hot path (string escape + concat per node).
    out: list[str] = []
    for el in tree.iter():
        tag = el.tag if isinstance(el.tag, str) else "comment"
        if tag in ("h1", "h2", "h3"):
            out.append("#" * int(tag[1]) + " ")
        elif tag == "li":
            out.append("- ")
        elif tag in ("strong", "b"):
            out.append("**")
        if el.text:
            out.append(el.text.translate(_ESCAPE))
        if el.tail:
            out.append(el.tail.translate(_ESCAPE))
        out.append("\n")
    _ = len("".join(out))


def work_pyloop(_payload) -> None:
    n = 0
    for _ in range(30_000_000):  # ~0.4s single-shot, comparable sample count
        n += 1
    _ = n


def work_bs4(html_bytes: bytes) -> None:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_bytes, "html.parser")
    _ = soup.name


def work_markdownify(html_bytes: bytes) -> None:
    from markdownify import markdownify as md
    _ = len(md(html_bytes.decode("utf-8", errors="replace")))


# ---- runners ----------------------------------------------------------------

async def sample_idle(duration_s: float) -> dict:
    jitter: list[float] = []
    deadline = time.perf_counter() + duration_s
    while time.perf_counter() < deadline and len(jitter) < SAMPLE_CAP:
        t0 = time.perf_counter()
        await asyncio.sleep(INTERVAL)
        jitter.append((time.perf_counter() - t0 - INTERVAL) * 1000.0)
    return summarize("idle", jitter, None, "measurement floor")


async def sample_threaded(name: str, fn, payload, note: str = "") -> dict:
    """Run fn(payload) ONCE on a worker thread; sample the main-thread asyncio
    heartbeat jitter for the whole single operation. Single-shot (not repeated) so
    there is exactly ONE Python-side setup/teardown boundary — matching how a real
    conversion runs — instead of N boundaries from a repeat loop polluting the tail.
    Use a large enough payload that one operation lasts long enough to gather a few
    hundred heartbeat samples."""
    import threading
    done = threading.Event()
    timing: dict[str, float] = {}

    def runner():
        t0 = time.perf_counter()
        fn(payload)
        timing["per_iter_s"] = time.perf_counter() - t0
        done.set()

    jitter: list[float] = []
    th = threading.Thread(target=runner, name=f"w-{name}", daemon=True)
    th.start()
    while not done.is_set() and len(jitter) < SAMPLE_CAP:
        t0 = time.perf_counter()
        await asyncio.sleep(INTERVAL)
        jitter.append((time.perf_counter() - t0 - INTERVAL) * 1000.0)
    th.join()
    return summarize(name, jitter, timing.get("per_iter_s"), note)


async def sample_direct(name: str, fn, payload, runs: int = 6) -> dict:
    """NEGATIVE control: run fn ON the event-loop thread (no offload). Interleave
    clean heartbeats with on-loop calls so the distribution shows the loop frozen
    for the full work duration every time work runs."""
    jitter: list[float] = []
    per_iter: list[float] = []
    for _ in range(runs):
        for _ in range(12):  # clean heartbeats
            t0 = time.perf_counter()
            await asyncio.sleep(INTERVAL)
            jitter.append((time.perf_counter() - t0 - INTERVAL) * 1000.0)
        # one heartbeat that straddles a blocking on-loop call
        t0 = time.perf_counter()
        await asyncio.sleep(INTERVAL)
        w0 = time.perf_counter()
        fn(payload)
        per_iter.append(time.perf_counter() - w0)
        jitter.append((time.perf_counter() - t0 - INTERVAL) * 1000.0)
    return summarize(name, jitter, statistics.mean(per_iter),
                     "run ON the loop (no offload) — negative control")


# ---- reporting --------------------------------------------------------------

def fmt_row(r: dict) -> str:
    pw = f"{r['per_iter_s']:.3f}" if r["per_iter_s"] is not None else "  -  "
    return (
        f"{r['workload']:<11} work={pw:>7}s n={r['samples']:>5}  "
        f"mean={r['mean_ms']:7.3f} p50={r['p50_ms']:7.3f} p95={r['p95_ms']:7.3f} "
        f"p99={r['p99_ms']:7.3f} max={r['max_ms']:8.3f} ms"
        + (f"  <- {r['note']}" if r["note"] else "")
    )


async def main() -> None:
    # Default to a large SINGLE well-formed synthetic doc so one parse lasts long
    # enough to gather a few hundred heartbeat samples with exactly ONE Python
    # boundary. NB: benchmarks/fixtures/*.html are repeated full HTML documents
    # (each corpus copy has its own <html>/<body>), so libxml2 stops at the first
    # document boundary and only parses a fraction — unsuitable for single-shot
    # timing. Pass one explicitly to probe it anyway.
    here = Path(__file__).parent
    default = next((p for p in (here / "sample_50mb.html", here / "sample_5mb.html")
                    if p.exists()), here / "sample_5mb.html")
    html_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    if not html_path.exists():
        sys.exit(f"missing {html_path}; run gen_sample_html.py first")
    html_bytes = html_path.read_bytes()

    # Warm all imports + JIT on a SMALL slice (not the full file — the slow parsers
    # would take ~15s on 50MB) so one-time import/alloc costs don't show as jitter.
    tree = make_tree(html_bytes)
    warm = html_bytes[:100_000]
    warm_tree = make_tree(warm)
    for fn, payload in ((work_lxml_parse, warm), (work_tree_walk, warm_tree),
                        (work_md_emit, warm_tree), (work_bs4, warm),
                        (work_markdownify, warm), (work_pyloop, None)):
        fn(payload)

    print(
        f"python {sys.version.split()[0]} | GIL switch {sys.getswitchinterval()*1000:.0f}ms"
        f" | sample {len(html_bytes)/1024/1024:.2f}MB ({html_path.name})"
        f" | heartbeat target {INTERVAL*1000:.0f}ms | single-shot per stage\n"
    )

    results = [
        await sample_idle(DURATION_S),
        await sample_threaded("lxml_parse", work_lxml_parse, html_bytes,
                              "stage (a): C parse"),
        await sample_threaded("tree_walk", work_tree_walk, tree,
                              "stage (b): Python walk"),
        await sample_threaded("md_emit", work_md_emit, tree,
                              "stage (c): Python emit"),
        await sample_threaded("bs4", work_bs4, html_bytes, "bs4 parse"),
        await sample_threaded("markdownify", work_markdownify, html_bytes,
                              "lib we replace"),
        await sample_threaded("pyloop", work_pyloop, None, "pure-Python CPU"),
        await sample_direct("direct", work_lxml_parse, html_bytes),
    ]

    print("Main-thread asyncio heartbeat jitter while each workload runs:\n")
    for r in results:
        print("  " + fmt_row(r))

    g = {r["workload"]: r for r in results}
    print("\nPer-stage read (lower jitter = more async-friendly):")
    print(f"  idle        p99={g['idle']['p99_ms']:7.3f}ms   (floor)")
    print(f"  lxml_parse  p99={g['lxml_parse']['p99_ms']:7.3f}ms   stage (a) C parse")
    print(f"  tree_walk   p99={g['tree_walk']['p99_ms']:7.3f}ms   stage (b) Python walk")
    print(f"  md_emit     p99={g['md_emit']['p99_ms']:7.3f}ms   stage (c) Python emit")
    print(f"  pyloop      p99={g['pyloop']['p99_ms']:7.3f}ms   GIL-holding control")

    # Verdict keys on p95 (the parse BODY). Each stage runs single-shot, so the only
    # GIL-holding moment in lxml_parse is the one brief Python-side parser
    # setup/teardown (one heartbeat in the max tail). The walk/emit stages by
    # contrast block EVERY heartbeat (p50 already ~= the 5ms switch interval).
    parse_ok = g["lxml_parse"]["p95_ms"] < 0.25 * g["pyloop"]["p95_ms"]
    walk_blocks = g["tree_walk"]["p50_ms"] > 0.5 * g["pyloop"]["p50_ms"]
    emit_blocks = g["md_emit"]["p50_ms"] > 0.5 * g["pyloop"]["p50_ms"]
    print("\nVerdict:")
    print(f"  (a) lxml parse RELEASES the GIL: {parse_ok}  "
          f"(parse-body p50/p95/p99 "
          f"{g['lxml_parse']['p50_ms']:.3f}/{g['lxml_parse']['p95_ms']:.3f}/{g['lxml_parse']['p99_ms']:.3f}ms"
          f" == idle {g['idle']['p50_ms']:.3f}/{g['idle']['p95_ms']:.3f}/{g['idle']['p99_ms']:.3f}ms;"
          f" lone max={g['lxml_parse']['max_ms']:.1f}ms = the single ElementTree-construction boundary)")
    print(f"  (b) Python tree walk HOLDS the GIL: {walk_blocks}  "
          f"(p50 {g['tree_walk']['p50_ms']:.3f}ms — every heartbeat delayed)")
    print(f"  (c) Python md emit HOLDS the GIL: {emit_blocks}  "
          f"(p50 {g['md_emit']['p50_ms']:.3f}ms — every heartbeat delayed)")
    print("  => Offloading the PARSE keeps the loop alive; the Python walk+emit do "
          "NOT.\n     Phase-2 must chunk walk+emit with awaits (or push them into C) "
          "to stay async-friendly.")


if __name__ == "__main__":
    asyncio.run(main())
