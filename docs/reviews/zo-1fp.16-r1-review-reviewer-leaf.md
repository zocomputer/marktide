# Code Review: zo-1fp.16 (R1, reviewer-leaf)

- Bead: zo-1fp.16
- Commit range: 91b5d36..c03cf4e (plus docs update a9ea3b5)
- Plan doc: docs/test-plan.md
- Reviewer: reviewer-leaf
- Review commit: fb8cb92

## Findings

### P1 - Passing concatenation property is still coded as an xfail-on-regression

**Location:** `tests/property/test_metamorphic.py:101-114`

**Problem**

`tests/property/test_metamorphic.py::test_concatenation_homomorphism` currently passes against the real converter, and coder-1-leaf's review request lists it as a passing relation. However, the test still has a dynamic `pytest.xfail(...)` branch whenever `combined != separate`. If the converter regresses tomorrow, this relation will turn into an expected failure instead of failing the property suite.

That turns a claimed green metamorphic property into a non-enforcing smoke test. The xfail reason is also stale (`"block-boundary paragraph emission is not wired yet; this relation should pass once block handlers land"`), which no longer matches the current implementation state.

**Suggested fix**

Remove the `if combined != separate: pytest.xfail(...)` block from `test_concatenation_homomorphism` and let the assertion fail normally. Keep the documented CommonMark round-trip xfail if that is still an intentional non-gating relation.

---

### P1 - `test_html_generator_smoke` is generative but lacks the hard wall-clock wrapper

**Location:** `tests/property/test_metamorphic.py:155-158`

**Problem**

The bead's critical directive is to tightly bound **all** generative runs with low `max_examples`, per-example deadlines, and a hard wall-clock timeout wrapping each suite/test. The main metamorphic properties use `@bounded_runtime()`, but `test_html_generator_smoke` is also a Hypothesis test (`@given(html_document())`) and does not have the hard wall-clock wrapper.

The fast Hypothesis profile still caps examples and per-example deadline, so the current run is fast, but this test is the one place where a generator bug or shrink-time explosion can run without the same 10 s suite-level alarm as the other generative tests.

**Suggested fix**

Add `@bounded_runtime()` above `@given(html_document())` on `test_html_generator_smoke`, matching the other property tests.

---

### P1 - Property suite files fail the project lint command

**Location:** `tests/property/test_metamorphic.py:23-27`

**Problem**

`uv run ruff check tests/property/conftest.py tests/property/html_strategies.py tests/property/test_metamorphic.py` fails with E402:

```text
E402 Module level import not at top of file
  --> tests/property/test_metamorphic.py:27:1
27 | from html_strategies import block_html, html_document, html_fragment_pair
```

The project instructions require lint to pass before committing, and this suite currently cannot pass ruff as committed.

**Suggested fix**

Avoid mutating `sys.path` before a module-level import, or mark the import with a targeted `# noqa: E402` if the local strategy-module import is intentionally path-injected. A cleaner option is to make `tests/property` a package and use a relative import, or move the strategies into an importable test helper package.

## Tests run

- `uv run --group benchmark pytest tests/property -vv` → 5 passed, 1 xfailed in 4.91s
- `uv run ruff check tests/property/conftest.py tests/property/html_strategies.py tests/property/test_metamorphic.py` → failed with E402 in `tests/property/test_metamorphic.py:27`

## Summary

3 findings: 0 P0, 3 P1, 0 P2, 0 P3

**Verdict**: Not approved

## Disposition

| # | Severity | Finding | Disposition | Commit | Notes |
|---|----------|---------|-------------|--------|-------|
| 1 | P1 | Passing concatenation property is still coded as an xfail-on-regression | Incorporated | this commit | Removed the dynamic `pytest.xfail(...)` from `tests/property/test_metamorphic.py::test_concatenation_homomorphism`; reviewer confirmed proposed disposition via h2. |
| 2 | P1 | `test_html_generator_smoke` is generative but lacks the hard wall-clock wrapper | Incorporated | this commit | Added `@bounded_runtime()` to `tests/property/test_metamorphic.py::test_html_generator_smoke`; reviewer confirmed proposed disposition via h2. |
| 3 | P1 | Property suite files fail the project lint command | Incorporated | this commit | Added targeted `# noqa: E402` to the intentional path-injected `html_strategies` import; reviewer confirmed proposed disposition via h2. |
