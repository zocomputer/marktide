# Code Review: zo-1fp.11 (R3, reviewer-leaf)

- Bead: zo-1fp.11
- Commit range: 141c6b6..cc46d58 (item-D whitespace trim + CDATA follow-up)
- Plan doc: docs/design.md
- Reviewer: reviewer-leaf
- Review commit: 133be58

## Findings

### P1 - `blockquote_nested` remains unconditionally xfailed in the committed regression suite

**Location:** `tests/unit/html2md/test_block_inline_handlers.py:7-10`, `tests/unit/html2md/test_block_inline_handlers.py:26-31`, `tests/unit/html2md/test_block_inline_handlers.py:43-44` (committed `HEAD:tests/unit/html2md/test_block_inline_handlers.py`)

**Problem**

The item-D implementation in `src/html2md/emitter.py:105-151`, `src/html2md/emitter.py:210-221`, and `src/html2md/emitter.py:234-245` now makes the `blockquote_nested` corpus case pass (`convert("<blockquote>Outer <blockquote>Inner</blockquote></blockquote>") == "> Outer\n> > Inner"`). However, the committed `tests/unit/html2md/test_block_inline_handlers.py` still documents item-D as not landed, keeps `EMITTER_PENDING["blockquote_nested"]`, and calls `pytest.xfail(...)` before asserting the golden value. That means the exact regression item-D was supposed to lock down still reports as an expected failure instead of failing the build if the one-event whitespace lookahead regresses.

I do see an uncommitted working-tree edit that removes this xfail, but the committed review target does not include it yet.

**Suggested fix**

Commit the existing local removal (or equivalent): update the module docstring to say item-D has landed, delete `EMITTER_PENDING`, and let `test_block_inline_golden` always assert `convert(case["input_html"]) == case["expected_markdown"]` for `blockquote_nested`.

---

### P1 - CDATA preservation still drops leading `>` and corrupts CDATA sections containing `<`

**Location:** `src/html2md/emitter.py:269-273`

**Problem**

`MarkdownEmitter.comment` only emits CDATA when lxml delivers one complete comment callback whose text starts with `[CDATA[` and ends with `]]`. lxml's HTML parser does not always deliver CDATA that way. For CDATA content containing markup delimiters, the target stream splits the section and the implementation either drops the leading `>` or emits the trailing `]]>` as literal text.

Reproduction against the current code:

```python
from html2md import convert

assert convert("<![CDATA[foobar]]>") == "foobar"          # passes
assert convert("foo <![CDATA[>&<]]>") == "foo >&<"       # fails: returns "foo &<]]>"
```

The second case is not synthetic: CommonMark includes this exact CDATA shape, and the conformance harness still reports `commonmark:0630` as failing for `html2md` (`foo >&<` expected vs `foo &<]]>` actual). This means the CDATA follow-up only fixed the simple `markdownify:test_advanced:39` case, not CDATA preservation generally.

**Suggested fix**

Handle CDATA before lxml HTML parsing can split it, or add a small target-level CDATA reconstruction state that recognizes `[CDATA[` comment prefixes and consumes subsequent data events through the matching `]]>` delimiter before passing the recovered content through `emit_text`. Add regression coverage for at least `<![CDATA[foobar]]>`, `foo <![CDATA[>&<]]>`, and a multiline CDATA body containing `<`/`&`.

## Positive notes

- The one-event `Frame.pending_ws` design in `src/html2md/state.py:38-46` and the resolution points in `src/html2md/emitter.py:130-149`, `src/html2md/emitter.py:212-221`, and `src/html2md/emitter.py:239-245` are the right bounded-lookahead shape for item-D.
- Manual split-point checks for block/inline and nested-blockquote samples matched `convert_stream([...])` to `convert(...)`, so I did not find a chunk-invariance issue in the whitespace deferral itself.

## Tests run

- `uv run pytest tests/unit/html2md tests/conformance -q` → 284 passed, 1 xfailed in 0.40s
- `uv run ruff check src/html2md/emitter.py src/html2md/state.py` → passed
- Manual differential snippets for `blockquote_nested`, inline whitespace retention, block-sibling whitespace dropping, `pre`, ordinary comments, and CDATA edge cases
- Targeted CommonMark CDATA differential for the CDATA cases in `tests/conformance/fixtures/commonmark-spec/spec.txt`

## Summary

2 findings: 0 P0, 2 P1, 0 P2, 0 P3

**Verdict**: Not approved
