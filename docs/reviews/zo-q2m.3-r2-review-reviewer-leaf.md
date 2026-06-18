# Code Review: zo-q2m.3 (R2, reviewer-leaf)

- Bead: zo-q2m.3
- Commit range: 0ea3e4d..d704d92
- Reviewed commits: d704d92
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: d704d92

## Findings

No findings.

## R1 disposition

- R1 P1 (`README.md:198-201`, `README.md:217-220` overclaimed that the Rust one-shot libraries / faithful Rust converters are faster in raw wall time): fixed. `README.md:200-202` now says `htmd_py` and `html2text_rs` are faster while `html_to_markdown` is roughly tied with marktide, and `README.md:217-221` now says only two Rust one-shots post lower raw wall times.

## Verification notes

- The revised README prose matches `benchmarks/results/phase3.json`: `marktide_streaming.conversion_wall_s = 4.726884124975186`, `html_to_markdown.conversion_wall_s = 4.783535708033014`, `htmd_py.conversion_wall_s = 1.713718582992442`, and `html2text_rs.conversion_wall_s = 3.0331452499958687`.
- Recomputed the visible `xlarge` table values at `README.md:209-213` from `benchmarks/results/phase3.json`; the wall times, speed multiples, RSS deltas, missed-beat percentages, and `marktide_streaming` TTFO all match the committed benchmark data after rounding.
- Re-ran `make verify-fidelity`; primary effective fidelity remains `298/298`, raw fidelity remains `296/298`, and streaming parity remains `0/1107` mismatches.

## Commands run

- `git show --stat --patch d704d92 -- README.md`
- `python - <<'PY' ...` to recompute the `xlarge` table values from `benchmarks/results/phase3.json`.
- `make verify-fidelity`

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
