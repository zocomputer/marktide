# Code Review: zo-1fp.21 (R3, reviewer-leaf)

- Bead: zo-1fp.21
- Commit range: d5cb904..b86273b
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: b86273b

## Findings

No findings.

## R2 disposition verification

- R2 P1 (`README.md:119-120` claimed `244.7 MiB` RSS was below a `110 MiB` input): resolved. `README.md:121-126` now frames the evidence as sub-linear RSS scaling and lower RSS relative to `markdownify`, not absolute-below-input memory.
- R2 P2 (`README.md:88-91` overgeneralized Rust async stalls): resolved. `README.md:88-93` now specifically identifies `htmd_py` and `html_to_markdown` as the Rust converters that stall the event loop, while separately saying `html2text_rs` stays responsive but is lower-fidelity.

## Positive notes

- The memory scaling numbers in `README.md:121-124` match `benchmarks/results/phase3.json`: `html2md_streaming` peak-RSS-to-input ratio falls from `7.6546×` on `small` to `2.2277×` on `xlarge`, while `markdownify` is `25.5714×` on `xlarge`; `244.7 MiB` vs `2808.9 MiB` is the documented `11.5×` RSS gap.
- The benchmark commands at `README.md:141-150` still match the committed `benchmarks/` uv project entrypoints reviewed under `zo-1fp.22`.
- The fidelity verification line at `README.md:128-131` still matches the `make verify-fidelity` command reviewed under `zo-1fp.23`.

## Checks run

- Reviewed `README.md:86-150` against `benchmarks/results/phase3.json`, `benchmarks/results/report.md`, and the committed benchmark/fidelity verification entrypoints.
- Computed `benchmarks/results/phase3.json` memory ratios for `html2md_streaming` and `markdownify` to verify the README scaling claims.

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
