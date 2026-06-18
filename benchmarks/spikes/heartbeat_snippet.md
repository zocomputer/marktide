# Heartbeat-jitter metric shape (from gil_probe.py, bead zo-1fp.4)

Reusable for the Rust-candidate GIL check. Core idea: main thread runs a tight
asyncio sleep loop; the worker (parse) runs on a thread; "jitter" =
actual_elapsed - target per sleep. Report p50/p95/p99/max in ms.

## Sampler (drop-in)
```python
import asyncio, time, statistics, threading

INTERVAL = 0.001  # 1ms target heartbeat

async def sample_threaded(fn, payload, duration_s=1.5):
    done = threading.Event()
    def runner():
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < duration_s:
            fn(payload)            # the Rust call goes here
        done.set()
    jitter = []
    th = threading.Thread(target=runner, daemon=True); th.start()
    while not done.is_set():
        t0 = time.perf_counter()
        await asyncio.sleep(INTERVAL)
        jitter.append((time.perf_counter() - t0 - INTERVAL) * 1000.0)  # ms
    th.join()
    s = sorted(jitter)
    pct = lambda q: s[min(len(s)-1, int(q*len(s)))]
    return dict(n=len(s), mean=statistics.mean(s),
                p50=pct(.5), p95=pct(.95), p99=pct(.99), max=max(s))
```

## Metric shape (dict per workload)
{workload, per_iter_s, samples, mean_ms, p50_ms, p95_ms, p99_ms, max_ms}

## Reference baselines on my box (5MB HTML, CPython 3.12, 5ms GIL switch)
- idle (floor):        p50 0.15  p95 0.19  p99 0.20  max 2.6
- lxml parse (releases GIL):  p50 0.15  p95 0.19  p99 7.6   max 10.5
- pyloop / bs4 (hold GIL):    p50 ~12   p95 ~13   p99 12-109

## How to read for a Rust candidate
- If the Rust parse RELEASES the GIL (PyO3 `Python::allow_threads`), its p50/p95
  should sit at idle (~0.15ms). That's the green signal.
- If p50 jumps to ~switch-interval (~5-12ms on every sample), it HOLDS the GIL —
  i.e. the binding didn't wrap the heavy work in allow_threads.
- Key nuance: parse releasing the GIL is necessary but NOT sufficient. If the Rust
  lib returns a tree you then walk/emit in Python, that Python stage reacquires the
  GIL (I measured this: tree_walk + md_emit both pin every heartbeat at ~12ms).
  Prefer a Rust API that returns the finished Markdown STRING in one call, so the
  whole conversion stays inside allow_threads.

Full harness: benchmarks/spikes/gil_probe.py in the marktide repo.
