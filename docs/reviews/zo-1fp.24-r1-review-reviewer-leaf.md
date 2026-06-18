# Code Review: zo-1fp.24 (R1, reviewer-leaf)

- Bead: zo-1fp.24
- Commit range: 4bdaa68
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 4bdaa68

## Findings

### P1 - Guardrail corpus description overclaims semantic comparison against upstream dialects

**Location:** `README.md:99-102`, `tests/conformance/differential.py:416-446`

**Problem**

The README says the Turndown, CommonMark, and Pandoc guardrail corpora are compared semantically because those libraries emit different Markdown dialects: `the output is rendered back to HTML and the structure compared`.

That is not what the current differential harness does for all guardrail layers. In `tests/conformance/differential.py:416-446`, every case first gets a `markdownify_default_oracle` output. The semantic rendered-HTML comparison is used only when `case.layer == "commonmark_expected_html"`; all other layers, including `turndown`, `turndown_options`, and `pandoc`, compare normalized Markdown strings against the markdownify oracle output. The harness does not compare html2md output to upstream Turndown or Pandoc Markdown dialects, and it does not render those layers back to HTML for structural comparison.

This matters because the README is presenting the guardrail tier as stronger and broader than it currently is. The accurate story is still useful: these are upstream-derived HTML input corpora that exercise additional shapes, with CommonMark using rendered-HTML semantic comparison and Turndown/Pandoc currently run through the markdownify-oracle differential path.

**Suggested fix**

Replace the guardrail paragraph with wording that matches the harness. For example: `Guardrail / triangulation (809 cases). Turndown fixtures (147), CommonMark expected-HTML examples (654), and Pandoc HTML fixtures (8) broaden the HTML shape corpus beyond markdownify. They are diagnostic, not the drop-in fidelity headline: CommonMark is compared by rendered-HTML semantic equivalence, while Turndown and Pandoc currently use the same normalized markdownify-oracle comparison as extra regression coverage.`

---

### P2 - “Every corpus is pulled from upstream” excludes the hand-authored golden corpus

**Location:** `README.md:91-106`, `tests/conformance/sources.toml`, `tests/conformance/golden/*.json`

**Problem**

The README's primary tier includes `a hand-authored per-handler + edge-case golden corpus (64 cases)` at `README.md:91-93`, but the next paragraph says `Every corpus is pulled from its upstream project and pinned to an immutable commit` at `README.md:104-106`. The golden corpus is not pulled from an upstream project and is not listed in `tests/conformance/sources.toml` as an upstream-pinned source; it lives under `tests/conformance/golden/*.json`.

**Suggested fix**

Qualify the sentence: `Upstream-derived corpora are pinned to immutable commits in tests/conformance/sources.toml; the hand-authored golden corpus lives in tests/conformance/golden/ and is versioned in this repository.`

## Positive notes

- The corpus counts in `README.md:88-100` are correct: `markdownify_tests` `234` + `golden` `64` = `298` primary cases; `turndown` `125` + `turndown_options` `22` + `commonmark_expected_html` `654` + `pandoc` `8` = `809` guardrail cases; total `1107`.
- The primary fidelity numbers in `README.md:91-97` match `make verify-fidelity`: raw `296/298 = 99.3%`, effective `298/298 = 100%`, and streaming parity `0/1107`.
- The reproduction commands at `README.md:108-110` are valid: `make verify-fidelity` and `make conformance` both pass.

## Checks run

- `make verify-fidelity`
- `make conformance`
- `uv run --group benchmark python - <<'PY' ... load_cases() count check ... PY`
- Reviewed `README.md:86-115`, `tests/conformance/sources.toml`, and `tests/conformance/differential.py:416-446`.

## Summary

2 findings: 0 P0, 1 P1, 1 P2, 0 P3

**Verdict**: Not approved

## Disposition (R1 → R2, coder-2-leaf)

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | P1 | Claimed all guardrail corpora are compared by rendering back to HTML; only commonmark does | **Fixed** — guardrail paragraph now states html2md's output is compared to the markdownify oracle after normalization, and **only the CommonMark layer** adds the render-back-to-HTML semantic check (matches `differential.py` run_differential: `commonmark_semantic_equal` for `commonmark_expected_html`, normalized text equality otherwise). |
| 2 | P2 | "Every corpus pulled from upstream and pinned" excludes the hand-authored golden set | **Fixed** — now "the *external* corpora are pulled upstream and pinned in sources.toml; the 64-case golden set is hand-authored (oracle-generated) under tests/conformance/golden/." |
