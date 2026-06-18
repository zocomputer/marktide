# Code Review: zo-1fp.21 (R2, reviewer-leaf)

- Bead: zo-1fp.21
- Commit range: c7bd68b
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: c7bd68b

## Findings

### P1 - README memory bullet now says the measured RSS is below the input size, but it is not

**Location:** `README.md:119-120`

**Problem**

The R2 text says peak RSS growth is `244.7 MiB on a 110 MiB input — far below the document size`. That is numerically false: `244.7 MiB` is about `2.2×` the `~110 MiB` fixture size, not far below it.

This reintroduces an overclaim in the memory framing. The supported claim is that `html2md_streaming` has a much lower process-RSS slope than the semantic contenders and avoids building a full DOM. It is not that measured process RSS is below the document size.

**Suggested fix**

Change the parenthetical to something like: `244.7 MiB on a 110 MiB input, versus 2808.9 MiB for markdownify and 4306.6 MiB for html_to_markdown`. Keep the `builds no full DOM` explanation, but do not say the process-RSS delta is below the input size.

---

### P2 - Opening benchmark framing still overgeneralizes Rust async stalls

**Location:** `README.md:88-91`

**Problem**

The opening benchmark paragraph still says `the Rust one-shot converters are faster in raw wall time but stall the event loop and use multiple GiB of memory`. That remains too broad for the committed phase-3 table: `README.md:100` shows `html2text_rs` at `0.4%` missed event-loop beats, and the detailed paragraph at `README.md:105-108` correctly says `html2text_rs` releases the GIL but fails on fidelity.

The detailed paragraph is fixed, but the top-level framing still contradicts it.

**Suggested fix**

Use the same qualified framing as the detailed paragraph. For example: `the Rust one-shot converters are faster in raw wall time but fail other axes: html_to_markdown/htmd_py stall the event loop, html2text_rs is low-fidelity, all are non-streaming, and all use much more memory than html2md`.

## Positive notes

- The R1 fidelity issue is resolved against the current committed artifacts: `README.md:110-124`, `tests/conformance/reports/latest.md`, and `make verify-fidelity` now agree on primary `296/298` raw = `99.3%` and effective `298/298` = `100%`.
- The benchmark commands at `README.md:135-145` now point at the committed self-contained `benchmarks/` uv project and match `benchmarks/pyproject.toml` script entrypoints.
- The detailed async bullet at `README.md:114-116` now distinguishes `html_to_markdown`/`htmd_py` from `html2text_rs`.

## Checks run

- Reviewed `README.md:86-145` against `benchmarks/results/phase3.json`, `benchmarks/results/report.md`, `tests/conformance/reports/latest.md`, and the committed `benchmarks/` uv project entrypoints.
- Reused current verified outputs from `make verify-fidelity`, `cd benchmarks && uv run bench`, and `cd benchmarks && uv run bench-async-starvation` run during adjacent `zo-1fp.23` / `zo-1fp.22` reviews.

## Summary

2 findings: 0 P0, 1 P1, 1 P2, 0 P3

**Verdict**: Not approved
