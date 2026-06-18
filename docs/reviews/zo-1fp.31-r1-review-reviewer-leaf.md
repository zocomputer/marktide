# Code Review: zo-1fp.31 (R1, reviewer-leaf)

- Bead: zo-1fp.31
- Commit range: 00f7b3f
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 00f7b3f

## Findings

### P1 - Canonical example files are not linked from the README

**Location:** `README.md`, `examples/canonical.html`, `examples/canonical.md`, `examples/README.md:1-12`

**Problem**

The bead explicitly requires committing `examples/canonical.html` plus `examples/canonical.md` and linking both from the README. Commit `00f7b3f` adds the example files and `examples/README.md`, but `README.md` does not mention or link `examples/canonical.html`, `examples/canonical.md`, `examples/README.md`, or `make verify-canonical`.

In a clean checkout at `00f7b3f`, searching the README for `canonical`, `verify-canonical`, and `examples/` only finds unrelated uses of “canonical” in the CommonMark option and benchmark-artifact wording. That leaves the canonical example undiscoverable from the project front page, which is part of the requested deliverable.

**Suggested fix**

Add a short README pointer near `README.md:86-159` (Correctness / Compatibility) or near the examples/status links. For example: `See examples/canonical.html and examples/canonical.md for a representative input/output pair; run make verify-canonical to compare rendered semantics across html2md, markdownify, html-to-markdown, and Pandoc when installed.`

## Positive notes

- `examples/canonical.html` and `examples/canonical.md` are committed and cover the requested representative feature set: h1-h6, paragraphs, bold/italic, links, image, inline code, fenced code block, blockquote, unordered and ordered lists, horizontal rule.
- `Makefile:45-46` exposes `make verify-canonical` as a sibling verification command.
- `tests/conformance/verify_canonical.py:1-106` checks that `examples/canonical.md` is not stale against live `html2md` output, renders Markdown back to HTML, reuses `tests/conformance/differential.py` canonical HTML normalization, compares `html2md`, `markdownify`, and `html-to-markdown`, and includes Pandoc when the executable is installed.
- In a clean detached worktree at `00f7b3f`, `uv run ruff check tests/conformance/verify_canonical.py` and `make verify-canonical` passed. Pandoc was skipped because no `pandoc` executable is installed in this environment; required converters all passed.

## Checks run

- Created a detached clean worktree at `/Users/dcosson/h2home/worktrees/reviewer-leaf-zo-1fp31` pinned to `00f7b3f`.
- `uv run ruff check tests/conformance/verify_canonical.py` — passed.
- `make verify-canonical` — passed for `html2md`, `markdownify`, and `html-to-markdown`; Pandoc skipped as not installed.
- Searched `README.md`, `Makefile`, `examples/README.md`, and `docs/usage.md` for `canonical`, `verify-canonical`, and `examples/` references.

## Summary

1 finding: 0 P0, 1 P1, 0 P2, 0 P3

**Verdict**: Not approved
