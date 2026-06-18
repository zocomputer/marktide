# Code Review: zo-1fp.29 (R1, reviewer-leaf)

- Bead: zo-1fp.29
- Commit range: 07cf2ce and 90434ee
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 90434ee

## Findings

### P1 - README says the listed edge cases are tracked in `allowed_divergences.toml`, but most are not

**Location:** `README.md:137-146`, `tests/conformance/allowed_divergences.toml`

**Problem**

The README table lists five guardrail examples: `<strike>`, `<h7>`, two whitespace-only `<span>` cases, and CDATA. Immediately after, `README.md:145-146` says: `These are tracked in tests/conformance/allowed_divergences.toml and surfaced by make verify-fidelity`.

That is false for most rows. `tests/conformance/allowed_divergences.toml` currently contains only:

- the two primary `markdownify:test_conversions:182` / `markdownify:test_conversions:183` heading parser divergences;
- `commonmark:0630` for the CDATA angle-bracket guardrail case;
- older golden candidates not active in the current primary/guardrail examples.

It does not track the Pandoc `<strike>` example or the Turndown `<h7>` / whitespace-span examples. `make verify-fidelity` also does not surface those individual Turndown/Pandoc cases as documented divergences; it only prints aggregate guardrail layer counts plus the active allowed divergences.

This matters because it tells readers these guardrail differences are allow-listed/documented in the machine-readable divergence ledger when they are not.

**Suggested fix**

Either add explicit entries for the Pandoc/Turndown rows to `tests/conformance/allowed_divergences.toml` and update `make verify-fidelity` to surface them if that is the intended contract, or change the README sentence to something accurate. For example: `The primary heading divergences and the CDATA guardrail divergence are tracked in tests/conformance/allowed_divergences.toml and surfaced by make verify-fidelity; the Pandoc/Turndown rows above are representative guardrail failures from tests/conformance/reports/latest.json.`

---

### P2 - README says each differing case is shown, but the guardrail failures are only representative

**Location:** `README.md:122-124`, `README.md:137-143`, `tests/conformance/reports/latest.json`

**Problem**

`README.md:122-124` says `The handful of cases that differ are edge/guardrail behaviors, all on invalid or ambiguous HTML; each is shown below`. The table does not show each current raw failure. `tests/conformance/reports/latest.json` has additional `html2md` CommonMark guardrail failures beyond `commonmark:0630`, including `commonmark:0176`, `commonmark:0177`, `commonmark:0182`, `commonmark:0193`, `commonmark:0627`, and `commonmark:0628`.

Also, not every listed guardrail example is invalid or ambiguous HTML. For example, `<strike>bar</strike>` and whitespace-only `<span>` cases are better described as convention/normalization choices, not invalid markup.

**Suggested fix**

Make the scope explicit. For example: `Representative differences are shown below as input → html2md → markdownify. The primary drop-in divergences are exhaustive; the guardrail rows are representative examples from diagnostic corpora and are not the primary contract.` Also change `all on invalid or ambiguous HTML` to `invalid markup, parser recovery, or convention/normalization choices`.

## Positive notes

- The concrete table outputs in `README.md:132-143` match the live converter/markdownify outputs for the listed snippets.
- The primary headline in `README.md:122-124` matches `make verify-fidelity`: raw `296/298`, effective `298/298`.
- The optional `Options.commonmark_roundtrip_stable` note in `README.md:148-154` correctly says the default remains strict markdownify-output compatibility.
- `docs/design.md` and `docs/test-plan.md` now point readers at the real shipped Makefile targets or clearly mark older plan target names as illustrative.

## Checks run

- Ran live converter/markdownify checks for the README examples using `uv run --group benchmark python`.
- `make verify-fidelity` — passed and printed primary `298/298` effective plus diagnostic guardrail rows.
- `uv run --group benchmark pytest tests/property -q` — passed at current HEAD after `a516265` (`7 passed, 1 xfailed`).
- Inspected `tests/conformance/allowed_divergences.toml` and current `tests/conformance/reports/latest.json` raw failures.

## Summary

2 findings: 0 P0, 1 P1, 1 P2, 0 P3

**Verdict**: Not approved
