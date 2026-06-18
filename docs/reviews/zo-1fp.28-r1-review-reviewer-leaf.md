# Code Review: zo-1fp.28 (R1, reviewer-leaf)

- Bead: zo-1fp.28
- Commit range: 1eb9a8f
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: 1eb9a8f

## Findings

### P1 - Stable-mode property does not pass for generated code-span inputs with edge spaces

**Location:** `tests/property/test_metamorphic.py:84-90`, `tests/property/test_metamorphic.py:190-200`, `src/html2md/rules/inline.py:116-139`

**Problem**

The bead requires the CommonMark round-trip property to pass when `Options.commonmark_roundtrip_stable=True`. The new property test does not pass on the committed code. Running `uv run --group benchmark pytest tests/property -q` at `1eb9a8f` fails with this minimized example:

```text
document = '<p><code>0 </code><code> 0</code></p>'
E       AssertionError: assert '`0` `0`' == '`0`  `0`'
E         - `0`  `0`
E         ?     -
E         + `0` `0`
```

The generator in `tests/property/test_metamorphic.py:84-90` includes spaces in `code_text`, including leading/trailing spaces. For these inputs, `_commonmark_stable_code_span()` in `src/html2md/rules/inline.py:116-139` only chooses a canonical backtick delimiter and pads edge backticks; it does not make the sibling/edge-whitespace output text-idempotent after Markdown render→HTML→convert. CommonMark collapses the inter-code-span whitespace, so the second conversion emits one space where the first emitted two.

This means the advertised stable mode is not yet proven by its own property test, and `make test` will fail whenever this Hypothesis example is discovered.

**Suggested fix**

Either make the stable-mode emission actually canonical for edge-whitespace code-span siblings, or narrow and document the property generator to the exact relation the mode is designed to guarantee. If edge-whitespace code spans are out of scope, `code_span_round_trip_document()` should not generate leading/trailing spaces and the test docstring/comment should explain that this mode addresses delimiter instability, not CommonMark whitespace canonicalization.

After the fix, rerun `uv run --group benchmark pytest tests/property -q` and `make test`.

## Positive notes

- `Options.commonmark_roundtrip_stable` defaults to `False` in `src/html2md/options.py:56-59`, and `make verify-fidelity` still reports primary effective `298/298 = 100.0%`, raw `296/298 = 99.3%` in default mode.
- The default code-span behavior remains split from the optional stable behavior in `src/html2md/rules/inline.py:105-157`.
- `tests/property/test_metamorphic.py:151-174` clearly documents why default markdownify-compatible mode is not text-idempotent for adjacent code spans and why the optional mode exists.
- The `zo-1fp.27` fixtureless collection blocker path is improved in `tests/component/test_chunk_invariance.py:176-190`; targeted component tests pass in the fixture-present checkout.

## Checks run

- `make lint` — passed.
- `make verify-fidelity` — passed and preserved the primary `298/298` effective default fidelity claim.
- `make conformance` — passed.
- `uv run --group benchmark pytest tests/component/test_chunk_invariance.py -q` — `1124 passed`.
- `uv run --group benchmark pytest tests/property -q` — failed as described above.

## Summary

1 finding: 0 P0, 1 P1, 0 P2, 0 P3

**Verdict**: Not approved
