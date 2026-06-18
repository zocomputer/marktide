# Code Review: zo-q2m.3 (R1, reviewer-leaf)

- Bead: zo-q2m.3
- Commit range: 0870277..0ea3e4d
- Reviewed commits: 0870277, 0ea3e4d
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 0ea3e4d

## Findings

### P1 - README still says every Rust one-shot converter is faster than marktide

**Location:** `README.md:198-201`, `README.md:217-220`

**Problem**

The updated table correctly says `marktide` streaming is `4.73 s` and `html_to_markdown` is `4.78 s` on the `xlarge` fixture (`README.md:210`, `README.md:213`). Those values match `benchmarks/results/phase3.json`: `marktide_streaming.conversion_wall_s = 4.726884124975186` and `html_to_markdown.conversion_wall_s = 4.783535708033014`.

The surrounding prose still claims that the faithful Rust converters are faster in raw wall time and that "The Rust one-shot libraries post lower raw wall times" (`README.md:198-201`, `README.md:217-220`). That was true before the Tier-1 re-run, but is false now for `html_to_markdown`: `marktide_streaming` is slightly faster (`4.73 s` vs `4.78 s`) while also streaming and staying async-friendly. Leaving this prose unchanged understates the Tier-1 result and contradicts the table.

**Suggested fix**

Change the prose to distinguish the competitors that are still faster from the one that is now slightly slower. For example:

- `README.md:198-201`: say the faithful Rust converters are competitive in raw wall time, with `htmd_py` faster and `html_to_markdown` roughly tied/slightly slower, but both stall the event loop.
- `README.md:217-220`: replace "The Rust one-shot libraries post lower raw wall times" with wording such as "Some Rust one-shot libraries post lower raw wall times" or explicitly name `htmd_py` and `html2text_rs`; keep the existing async/fidelity/memory distinctions.

## Verification notes

- Recomputed the `xlarge` README table from `benchmarks/results/phase3.json`: `markdownify` `54.55 s`, `2811.1 MiB`, `60.4%`; `html_to_markdown` `4.78 s`, `11.4×`, `3761.0 MiB`, `50.0%`; `htmd_py` `1.71 s`, `31.8×`, `1569.2 MiB`, `50.0%`; `html2text_rs` `3.03 s`, `18.0×`, `3906.7 MiB`, `0.4%`; `marktide_streaming` `4.73 s`, `11.5×`, `247.3 MiB`, `0.0%`, `2.2 ms`.
- Confirmed the memory-scaling prose at `README.md:231-235` is sourced from `benchmarks/results/phase3.json`: `marktide_streaming` RSS/input ratio `7.6546×` on `small`, `2.2517×` on `xlarge`; `markdownify` `25.5918×` on `xlarge`; `247.3 MiB` vs `2811.1 MiB` is an `11.4×` RSS gap.
- Confirmed `make verify-fidelity` still reports primary effective `298/298`, raw `296/298`, and streaming parity mismatches `0/1107`.

## Commands run

- `python - <<'PY' ...` to extract and recompute the `xlarge` README table values from `benchmarks/results/phase3.json`.
- `grep -RInE ... README.md docs benchmarks ...` to look for stale benchmark numbers; matches outside `README.md` were historical review/design artifacts or fixture content, not active README claims.
- `make verify-fidelity` — primary effective `298/298`, raw `296/298`, streaming parity `0/1107`.

## Summary

1 finding: 0 P0, 1 P1, 0 P2, 0 P3

**Verdict**: Not approved
