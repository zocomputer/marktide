# Code Review: zo-1fp docs deliverable (R1, reviewer-leaf)

- Bead: zo-1fp (docs deliverable; no dedicated docs bead found)
- Commit range: 15dc54a
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 15dc54a

## Findings

### P1 - User-facing compatibility claims say `html2md` fully matches `markdownify`, but current conformance still has known gaps/divergences

**Location:** `README.md:3-6`, `README.md:38-39`, `docs/usage.md:182-203`

**Problem**

The README and migration guide present `html2md` as having "the same options and output" as `markdownify` and say option names, defaults, and rendered Markdown match `markdownify==1.2.2` across markdownify's own test suite. That overstates the current implementation state.

Current project evidence still shows primary markdownify-oracle misses (`tests/conformance/reports/latest.json` has `html2md` at 294 passed / 4 failed across the primary golden + `markdownify_tests` layers, with `markdownify_tests` itself at 230 passed / 4 failed). There is also an open R3 foundation review finding in `docs/reviews/zo-1fp.11-r3-review-reviewer-leaf.md` for CDATA containing `<`, and `docs/usage.md:191-203` itself documents divergence classes.

This is not just wording polish: migration docs are a contract. A user swapping from `markdownify` based on "same options and output" will not know they need to account for documented parser/table divergences and current residual fidelity issues.

**Suggested fix**

Qualify the compatibility language everywhere it appears. For example:

- Replace "the same options and output" in `README.md:4-5` with "markdownify-compatible options and output for the supported/default surface, with documented divergences".
- Replace `README.md:38-39` and `docs/usage.md:184-189` with a measured statement such as "validated against markdownify's own test suite and a layered corpus; see the documented divergences and conformance report for the remaining edge cases".
- In `docs/usage.md:182-203`, make the "What's identical" section clearly scoped and include the active residual categories (or link to the conformance report / review findings) rather than saying all listed features behave the same.

---

### P1 - Streaming memory docs promise O(nesting depth), but the emitter buffers open block/table content

**Location:** `README.md:33-37`, `docs/usage.md:52-56`, `docs/usage.md:220-223`

**Problem**

The docs say streaming conversion is "bounded memory" and that a 100 MB document converts in `O(nesting depth), not O(document)`. That is stronger than the implementation can guarantee.

`src/html2md/emitter.py:90-98` writes output to the nearest buffering frame, and handlers intentionally buffer current element content until `end()` so they can render constructs like headings, code spans, lists, blockquotes, and tables. Large single blocks (for example a huge `<p>`, `<pre>`, or `<table>`) can therefore require memory proportional to that open block/table content, not just nesting depth. This is also visible in the E2E huge-tree test at `tests/e2e/test_blackbox.py:115-123`, which converts a >10 MB single text node as one paragraph; that paragraph has to survive until its closing tag.

The implementation still avoids materializing a full DOM and can stream completed top-level blocks, but the accurate bound is closer to "parser state + open element buffers / largest unclosed render unit," not pure `O(depth)`.

**Suggested fix**

Revise the memory claims to avoid an impossible asymptotic guarantee. For example:

- `README.md:34-35`: "avoids materializing a DOM and drains completed top-level blocks; memory is bounded by parser state plus currently open element buffers (large single blocks/tables are buffered until they close)."
- `docs/usage.md:54-56` and `docs/usage.md:220-223`: same qualification. Keep the early-output benefit, but specify that early output occurs after safe block boundaries, not for arbitrary still-open blocks.

## Tests / checks run

- Verified all committed Python examples in `README.md` and `docs/usage.md` against the live API with `uv run python`.
- Inspected public API and options in `src/html2md/__init__.py`, `src/html2md/convert.py`, and `src/html2md/options.py`.
- Checked current conformance summary in `tests/conformance/reports/latest.json`.

## Summary

2 findings: 0 P0, 2 P1, 0 P2, 0 P3

**Verdict**: Not approved
