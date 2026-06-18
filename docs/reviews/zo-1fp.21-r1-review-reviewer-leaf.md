# Code Review: zo-1fp.21 (R1, reviewer-leaf)

- Bead: zo-1fp.21
- Commit range: 450029d
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 450029d

## Findings

### P1 - README fidelity claim is not supported by the committed phase-3 artifacts

**Location:** `README.md:107-110`, `benchmarks/results/phase3.json`, `benchmarks/results/report.md:17-18`, `tests/conformance/reports/latest.json`

**Problem**

The README says `html2md` is faithful with `99.3% raw / 100% effective` normalized conformance. The committed phase-3 artifacts do not support that statement:

- `benchmarks/results/report.md:17-18` reports raw primary fidelity as `294/298 (98.658%)` and effective primary fidelity as `296/298 (99.329%)`.
- `tests/conformance/reports/latest.json` currently has `html2md` and `html2md_streaming` primary counts of `{passed: 294, failed: 4, error: 0}`.
- `benchmarks/results/phase3.json` is the phase-3 artifact the README says it is summarizing, and it corresponds to the same committed phase-3 snapshot.

So the README's `99.3% raw / 100% effective` is a newer/desired fidelity story, not the one backed by the committed `phase3.json` / `report.md` being cited in this section.

**Suggested fix**

Either:

1. Change the README claim to the committed phase-3 artifact numbers: raw `98.7%`, effective `99.3%`; or
2. Regenerate and commit the phase-3/conformance artifacts that support raw `99.3%` and effective `100%`, then keep the README claim.

Do not mix newer fidelity claims with older benchmark artifacts.

---

### P1 - Benchmark commands document uncommitted entrypoints

**Location:** `README.md:127-137`

**Problem**

The README says the harness is a self-contained uv project under `benchmarks/` and documents:

```bash
cd benchmarks && uv sync
uv run bench
uv run bench --full
uv run bench-async-starvation
```

At commit `450029d`, those entrypoints are not committed: there is no committed `benchmarks/pyproject.toml`, no committed `benchmarks/uv.lock`, and no committed console scripts named `bench` / `bench-async-starvation`. They exist only as untracked worktree files from the upcoming `zo-1fp.22` work.

That makes the README's "How we ran them" section non-reproducible in the committed state under review.

**Suggested fix**

Land `zo-1fp.22` first (including `benchmarks/pyproject.toml`, `benchmarks/uv.lock`, and the console-script entrypoints), then re-review README + benchmark project together. If README must land before `zo-1fp.22`, change this section to point only at currently committed commands (`make bench`, `uv run --group benchmark python -m benchmarks.harness.runner ...`, and `uv run --group benchmark python benchmarks/charts.py ...`) or explicitly label the new uv project as forthcoming.

---

### P1 - Rust async-stall framing overgeneralizes and contradicts the table

**Location:** `README.md:88-91`, `README.md:103-113`

**Problem**

The README says the Rust one-shot converters stall the event loop and later says "the Rust one-shot libraries" have `~50%` missed beats and p99 stalls of `1.6–4.6 s`. That is not true for all Rust rows in the phase-3 JSON/table:

- `html_to_markdown` and `htmd_py` are ~50% missed beats with multi-second stalls.
- `html2text_rs` is a Rust one-shot library, but the committed xlarge row is `0.4219%` missed beats with `p99_delay_ms = 1.33` and `max_delay_ms = 69.56`.

The table in `README.md:100` even shows `html2text_rs` at `0.4%` missed beats, so the prose contradicts the table immediately below it.

**Suggested fix**

Qualify the prose. For example: "Some Rust one-shot converters are faster in raw wall time but stall the event loop badly (`html_to_markdown`, `htmd_py`); `html2text_rs` has better heartbeat behavior but still cannot stream and is not markdownify-faithful." Keep the five-axis framing, but do not claim all Rust one-shot libraries miss ~50% of beats.

---

### P2 - "Bounded memory" wording overclaims the RSS evidence

**Location:** `README.md:116-117`

**Problem**

The README says peak RSS growth "stays flat" at `244.7 MiB on a 110 MiB input` because the streaming path builds no full DOM. The phase-3 RSS metric is process-level peak RSS delta, not the DSST live-register footprint. In `benchmarks/results/phase3.json`, `html2md_streaming` peak RSS grows with fixture size (`0.8 MiB`, `14.2 MiB`, `123.6 MiB`, `244.7 MiB`), so the report itself correctly phrases this as a much lower memory slope, not perfectly flat memory.

The README should preserve the docs-R2 precision: no full DOM and much lower RSS growth, with streaming/live-register memory bounded by open state/largest open block/table, but not absolute flat process RSS.

**Suggested fix**

Replace "peak RSS growth stays flat" with wording like "peak RSS growth has the lowest semantic-contender slope (244.7 MiB on the 110 MiB xlarge fixture, vs 2808.9 MiB for markdownify), because the streaming path avoids a full DOM and drains completed output." If you want to mention bounded memory, explicitly scope it to the streaming/live-register model rather than process RSS.

## Positive notes

- The xlarge table values for wall time, speedup vs markdownify, peak RSS growth, missed beats, and TTFC match `benchmarks/results/phase3.json` after rounding.
- The five-axis framing is directionally right: `html2md_streaming` is the only contender that combines strong markdownify fidelity with streaming, async health, and much lower memory growth.

## Checks run

- Parsed `benchmarks/results/phase3.json` and checked xlarge rows for all README table entries.
- Checked `tests/conformance/reports/latest.json` primary markdownify-oracle counts.
- Compared README prose against `benchmarks/results/report.md` and the prior docs-R2 compatibility/memory wording.

## Summary

4 findings: 0 P0, 3 P1, 1 P2, 0 P3

**Verdict**: Not approved
