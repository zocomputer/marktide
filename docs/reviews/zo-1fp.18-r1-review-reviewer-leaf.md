# Code Review: zo-1fp.18 (R1, reviewer-leaf)

- Bead: zo-1fp.18
- Commit range: 38ca6ec
- Plan doc: docs/test-plan.md (referenced by bead as test-plan §7.3; file not present in this checkout, so review used bead description + committed test code)
- Reviewer: reviewer-leaf
- Review commit: a2412a2

## Findings

### P1 - Always-on stream equivalence only uses one chunk when benchmark fixtures are absent

**Location:** `tests/e2e/test_blackbox.py:56-58`, `tests/e2e/test_blackbox.py:91-98`, `tests/e2e/test_blackbox.py:114-142`

**Problem**

`test_inline_convert_equals_stream` and `test_inline_async_paths_match_sync` call `_chunks(_INLINE_DOC.encode())`, and `_chunks` defaults to `64 * 1024` bytes. `_INLINE_DOC` is only a few hundred bytes, so both always-on inline stream checks feed exactly one chunk. The only default tests that exercise multiple chunks are `test_real_fixture_convert_equals_stream[small]` / `[medium]`, but those call `_load(name)` and are skipped if the gitignored `benchmarks/fixtures/*.html` files are absent (`tests/e2e/test_blackbox.py:61-67`).

That means a PR/CI environment without generated benchmark fixtures can pass `pytest tests/e2e` without any real multi-chunk coverage for `convert_stream` or `convert_stream_async`, even though this bead's core contract is black-box `convert == convert_stream` and async streaming equivalence. This is especially important because this suite already found a foundation chunk-boundary bug; the always-on path should keep at least one committed fixture split across multiple structural/text boundaries.

**Suggested fix**

Force the committed inline document through multiple chunks, for both sync and async streaming. For example, add a helper such as `_tiny_chunks(data: bytes) -> Iterator[bytes]` with a small chunk size (or call `_chunks(_INLINE_DOC.encode(), size=17)`) in `test_inline_convert_equals_stream` and `_collect_stream_async`. Keep the benchmark fixture tests as additional real-document coverage, but do not make multi-chunk coverage conditional on gitignored files being present.

## Notes

- The xfailed real-fixture stream checks are reasonable as temporary coverage for the known foundation chunk-invariance bug because they are `strict=False` and will turn into XPASS once the foundation fix lands.
- The nightly gate in `tests/e2e/conftest.py:20-37` worked as documented: default `pytest tests/e2e -vv` skipped large/xlarge, while `pytest tests/e2e --run-nightly -vv` ran them locally when fixtures were present.

## Tests run

- `uv run pytest tests/e2e -vv` → 9 passed, 4 skipped, 1 xfailed in 1.98s
- `uv run pytest tests/e2e --run-nightly -vv` → 12 passed, 2 xfailed in 38.91s
- `uv run ruff check tests/e2e/conftest.py tests/e2e/test_blackbox.py` → passed

## Summary

1 finding: 0 P0, 1 P1, 0 P2, 0 P3

**Verdict**: Not approved
