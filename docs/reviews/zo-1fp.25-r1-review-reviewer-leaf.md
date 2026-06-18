# Code Review: zo-1fp.25 (R1, reviewer-leaf)

- Bead: zo-1fp.25
- Commit range: 4879c95
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 4b800fa

## Findings

No findings.

## Positive notes

- `tests/conformance/verify_fidelity.py:144-160` now leads with the primary drop-in contract and a single unambiguous headline: effective `298/298 = 100.0%`; raw `296/298 = 99.3%`; primary unallowed failures `0`; primary allowed parser divergences `2`.
- `tests/conformance/verify_fidelity.py:170-187` clearly labels CommonMark/Pandoc/Turndown/all-layer rows as guardrail / triangulation diagnostics that do not change the primary result, and renames the aggregate row to `all_layers_diagnostic`.
- `tests/conformance/verify_fidelity.py:193-219` splits active documented divergences into primary-counted divergences and guardrail-only divergences, so `commonmark:0630` is no longer easy to confuse with a primary-fidelity exception.
- `tests/conformance/README.md:82-94` now documents the same primary-vs-guardrail framing.

## Checks run

- `make verify-fidelity`
- `uv run ruff check tests/conformance/verify_fidelity.py`
- `uvx ty check tests/conformance/verify_fidelity.py`
- `make conformance`

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
