# Code Review: `zo-1fp.2` benchmark harness scaffold

- Bead: `zo-1fp.2`
- Commits reviewed: `e755efe` + `497ae5c` (current harness state at `497ae5c`)
- Reviewer: `reviewer-leaf`
- Review commit: 3a82c3d2753b0d102cd6cade7b0e03278562060c
- Scope: `benchmarks/harness/{adapters/,probe.py,fixtures.py}` and `benchmarks/harness/test_*.py`

## Verification run

- `uv run --group benchmark pytest benchmarks/harness -q` → **6 passed**
- Additional manual sanity check: `probe_adapter(..., repeat_until_duration=False)` calls a test converter exactly once; `repeat_until_duration=True` repeats it.
- Additional failure-path repro: a converter that raises under `Placement.TO_THREAD` currently leaves the heartbeat loop waiting until an outer timeout.

## Findings

### P1 - `Placement.TO_THREAD` hangs forever if the converter raises

**Location:** `benchmarks/harness/probe.py:167-191`

**Problem**

`benchmarks.harness.probe._probe_to_thread` uses a `done = asyncio.Event()` and samples heartbeat jitter while `not done.is_set()` at `benchmarks/harness/probe.py:187-190`. The worker sets that event only after the conversion loop reaches `benchmarks/harness/probe.py:183`. If `convert(payload)` raises inside `await asyncio.to_thread(...)` at `benchmarks/harness/probe.py:173` or `benchmarks/harness/probe.py:176`, the worker task exits with an exception before setting `done`. The heartbeat loop never observes completion, so `probe_adapter(...)` hangs indefinitely and the original adapter error is only reported as an un-retrieved task exception.

I confirmed this with a tiny repro:

```python
await asyncio.wait_for(probe_adapter("boom", lambda _: (_ for _ in ()).throw(RuntimeError("boom")), b""), timeout=0.2)
```

The result was a timeout plus `Task exception was never retrieved`, not a propagated `RuntimeError`.

This matters for phase-1 infrastructure because missing optional dependencies, candidate API changes, malformed fixture crashes, or lxml parse failures should fail one benchmark row/report clearly. They must not wedge the whole go/no-go harness.

**Suggested fix**

Make the worker set completion in a `finally` block and propagate the worker exception after the sampling loop exits. For example:

- In `worker()`, wrap the conversion loop in `try/except/finally`, store `timing["exception"] = exc` on exception, and always call `done.set()` in `finally`.
- After `await worker_task` (or before returning), re-raise the stored exception or return an explicit errored result shape that the final runner can serialize.
- Add a regression test in `benchmarks/harness/test_probe.py` asserting that a raising converter under `Placement.TO_THREAD` returns/raises promptly and does not require an outer timeout.

---

### P2 - Fixture verification silently downgrades when the lockfile or a requested fixture entry is missing

**Location:** `benchmarks/harness/fixtures.py:40-65`, `benchmarks/harness/fixtures.py:81-89`

**Problem**

`benchmarks.harness.fixtures.load_fixture_set(..., verify_hashes=True)` loads an empty metadata map when `benchmarks/fixtures.lock.json` is absent (`benchmarks/harness/fixtures.py:81-83`) and skips verification for any fixture whose stem is missing from the lock (`benchmarks/harness/fixtures.py:62-65`). That behavior is useful for temporary unit tests, but it weakens the production benchmark path: a final runner using the default fixture root could accidentally benchmark locally mutated or ad-hoc generated fixtures without realizing verification was disabled.

The current committed lockfile exists and mutation is detected when metadata is present, so this is not blocking the scaffold. It should be tightened before the final runner becomes authoritative.

**Suggested fix**

Keep the current flexibility behind an explicit opt-out, but make the default production path strict:

- If `verify_hashes=True` and `lock_path` is the default `benchmarks/fixtures.lock.json`, raise if the lockfile is missing.
- If a requested fixture exists but has no lock entry, raise unless the caller passes `lock_path=None` or a new explicit `allow_unlocked=True` option.
- Add tests for missing-lockfile and missing-entry behavior.

---

### P3 - Normalized markdownify adapter name is easy to confuse with the default oracle

**Location:** `benchmarks/harness/adapters/base.py:57-63`, `benchmarks/harness/adapters/markdownify_adapter.py:29-62`

**Problem**

The adapter split is conceptually correct: `benchmarks.harness.adapters.markdownify_adapter.MarkdownifyAdapter` is the normalized performance/comparison mode, and `benchmarks.harness.adapters.markdownify_adapter.MarkdownifyDefaultOracleAdapter` preserves drop-in default semantics. However, the normalized adapter's public `name` is still just `"markdownify"` at `benchmarks/harness/adapters/markdownify_adapter.py:31`, while the default-oracle adapter is `"markdownify_default_oracle"` at `benchmarks/harness/adapters/markdownify_adapter.py:50`.

In final result tables, `markdownify` may be read as the incumbent default behavior even though it forces ATX headings and a single `"*"` bullet marker at `benchmarks/harness/adapters/markdownify_adapter.py:39-45`.

**Suggested fix**

Before final report generation, consider renaming the normalized adapter row to `markdownify_normalized` or `markdownify_perf_normalized`, and reserve `markdownify_default_oracle` (or simply `markdownify_default`) for the unmodified incumbent. At minimum, ensure the final result table prints the adapter `option_map.settings` prominently.

---

## Positive notes

- `benchmarks/harness/probe.py:113-152` now defaults to single-conversion mode, so `conversion_wall_s`, `output_bytes`, `output_hash`, and heartbeat jitter describe the same conversion. This resolves the earlier repeat-loop measurement pollution concern.
- `benchmarks/harness/probe.py:204-241` makes `Placement.INLINE` a sound negative control for blocking the event-loop thread.
- `benchmarks/harness/adapters/markdownify_adapter.py:48-62` adds a separate default-oracle adapter, so normalized benchmark mode no longer replaces drop-in oracle semantics.
- `benchmarks/harness/fixtures.py:92-99` verifies both fixture size and SHA-256 when lock metadata is present.
- `benchmarks/harness/probe.py:88-91` records output bytes and SHA-256 for the measured conversion, which is the right primitive to prevent silent empty-output/degenerate benchmark rows once the final runner asserts/report-checks it.

## Summary

3 findings: 0 P0, 1 P1, 1 P2, 1 P3

**Verdict**: Approved with revisions. Fix the `Placement.TO_THREAD` exception hang before relying on the harness for go/no-go evidence; the remaining findings can be handled as final-runner hardening/report-clarity work.

## Disposition

| # | Severity | Finding | Disposition | Commit | Notes |
|---|----------|---------|-------------|--------|-------|
| 1 | P1 | `Placement.TO_THREAD` hangs forever if the converter raises | Incorporated | this commit | `_probe_to_thread` now records exceptions, always sets the completion event in `finally`, and re-raises the original converter exception after heartbeat sampling exits. Added `test_to_thread_raises_promptly_when_converter_raises`. Reviewer confirmed re-raising is the desired shape. |
| 2 | P2 | Fixture verification silently downgrades when lockfile or entry is missing | Incorporated | this commit | `load_fixture_set(..., verify_hashes=True)` now raises for a missing provided/default lockfile and for requested fixtures missing lock entries. `lock_path=None` remains the explicit opt-out for ad-hoc tests. |
| 3 | P3 | Normalized markdownify adapter name is easy to confuse with the default oracle | Deferred | — | Reviewer confirmed this can defer to final result-table/reporting pass; current split is functionally correct and `markdownify_default_oracle` is already used by the differential harness. |

## Reviewer re-review signoff for `bee2353`

Date: 2026-06-18  
Reviewer: `reviewer-leaf`  
Incorporation commit reviewed: `bee2353` (`fix: incorporate harness review feedback`)

Verification performed:

- Ran `uv run --group benchmark pytest benchmarks/harness -q` → **9 passed**.
- Re-ran the original raising-converter repro under `Placement.TO_THREAD`; it now promptly re-raises `RuntimeError("boom")` instead of hanging behind an outer timeout.

Disposition confirmation:

- **P1 resolved.** `benchmarks.harness.probe._probe_to_thread` stores converter exceptions, always signals completion in `finally`, and re-raises the original exception after heartbeat sampling exits.
- **P2 resolved.** `benchmarks.harness.fixtures.load_fixture_set(..., verify_hashes=True)` now hard-fails when a provided/default lockfile is missing or when an existing requested fixture lacks a lock entry. `lock_path=None` remains the explicit opt-out for ad-hoc fixtures/tests.
- **P3 accepted as deferred.** The normalized markdownify adapter row naming can be finalized in the result-table/reporting pass.

**Final verdict:** Approved for the current scaffold; no open blocker findings remain in this review.
