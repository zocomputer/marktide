"""v2 perf profiling harness (zo-q2m.1) — profile marktide emission overhead by stage.

Profile-first, no converter changes. Measures throughput per stage on a SINGLE
well-formed large doc (the repeated-doc xlarge fixture truncates at the first </html>
under lxml, so it would under-measure), and cProfiles convert() to attribute Python
time to escape / whitespace / collapse / buffering / dispatch.

Run: uv run python benchmarks/spikes/perf_profile.py [path]
"""

import cProfile
import io
import pstats
import sys
import time
from collections import defaultdict
from pathlib import Path

from lxml import etree

import marktide

HTML = Path(sys.argv[1] if len(sys.argv) > 1
            else "benchmarks/spikes/sample_50mb.html").read_bytes()
MB = len(HTML) / 1024 / 1024


class NoOp:
    def start(self, t, a): pass
    def end(self, t): pass
    def data(self, d): pass
    def comment(self, t): pass
    def close(self): return ""


class Counter:
    def __init__(self): self.n = 0
    def start(self, t, a): self.n += 1
    def end(self, t): pass
    def data(self, d): pass
    def comment(self, t): pass
    def close(self): return self.n


def timed(fn, n=3):
    best = 1e9
    for _ in range(n):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return best


def parse_noop():
    p = etree.HTMLParser(target=NoOp(), recover=True, huge_tree=True, encoding="utf-8")
    p.feed(HTML)
    p.close()


def parse_count():
    p = etree.HTMLParser(target=Counter(), recover=True, huge_tree=True, encoding="utf-8")
    p.feed(HTML)
    p.close()


def full_convert():
    marktide.convert(HTML)


def full_stream():
    chunks = [HTML[i:i + 65536] for i in range(0, len(HTML), 65536)]
    for _ in marktide.convert_stream(chunks):
        pass


def _walk(node, out):
    if isinstance(node.tag, str):
        out.append(node.text or "")
        for child in node:
            _walk(child, out)
            out.append(child.tail or "")


def naive_convert():
    # Inline lxml_naive reference: C parse + Python tree walk (no Markdown semantics).
    root = etree.fromstring(HTML, etree.HTMLParser(recover=True, huge_tree=True))
    out: list[str] = []
    _walk(root, out)
    _ = "".join(out)


def main():
    print(f"sample: {HTML.decode('utf-8', 'replace')[:0]}{Path(sys.argv[1] if len(sys.argv) > 1 else 'sample_50mb.html').name} "
          f"({MB:.1f} MiB)\n")
    print(f"{'stage':<34}{'time':>9}{'throughput':>14}")
    print("-" * 57)
    rows = [
        ("parse + no-op target (FLOOR)", parse_noop),
        ("parse + counting target", parse_count),
        ("lxml_naive (parse + py walk)", naive_convert),
        ("marktide.convert (one-shot)", full_convert),
        ("marktide.convert_stream 64KiB", full_stream),
    ]
    times = {}
    for name, fn in rows:
        t = timed(fn)
        times[name] = t
        print(f"{name:<34}{t:>7.3f}s{MB / t:>10.1f} MiB/s")

    floor = times["parse + no-op target (FLOOR)"]
    conv = times["marktide.convert (one-shot)"]
    print(f"\nemission overhead = convert - floor = {conv - floor:.3f}s "
          f"({100 * (conv - floor) / conv:.0f}% of convert)")
    print(f"streaming overhead = stream - convert = "
          f"{times['marktide.convert_stream 64KiB'] - conv:.3f}s "
          f"({100 * (times['marktide.convert_stream 64KiB'] - conv) / conv:+.0f}%)")

    # --- cProfile attribution of convert() Python time ---
    pr = cProfile.Profile()
    pr.enable()
    marktide.convert(HTML)
    pr.disable()
    st = pstats.Stats(pr)

    buckets = {
        "escape": ("escape", "_RE_ESCAPE", "replace"),
        "whitespace-norm": ("_RE_NEWLINE_WHITESPACE", "_RE_WHITESPACE", "_RE_ALL_WHITESPACE"),
        "collapse/fold": ("_fold_children", "_collapse_join", "_split_newlines", "_RE_EXTRACT"),
        "text/emit": ("emit_text", "emit", "_buf", "_flush_text", "_in_noformat"),
        "dispatch": ("start", "end", "data", "comment"),
    }
    by_bucket = defaultdict(float)
    total_tottime = 0.0
    for (_file, _line, func), (_cc, _nc, tottime, _ct, _cl) in st.stats.items():
        total_tottime += tottime
        placed = False
        for bucket, keys in buckets.items():
            if any(k.lower() in func.lower() for k in keys):
                by_bucket[bucket] += tottime
                placed = True
                break
        if not placed:
            by_bucket["other"] += tottime

    print(f"\ncProfile Python tottime breakdown (total {total_tottime:.3f}s):")
    for bucket, t in sorted(by_bucket.items(), key=lambda kv: -kv[1]):
        print(f"  {bucket:<18}{t:>7.3f}s  {100 * t / total_tottime:5.1f}%")

    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(20)
    print("\nTop functions by tottime:\n")
    print("\n".join(s.getvalue().splitlines()[5:30]))


if __name__ == "__main__":
    main()
