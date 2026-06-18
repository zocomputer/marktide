# Phase-2 conformance corpus

This directory stages external HTML→Markdown validation inputs for phase 2.

Committed files:

- `sources.toml` — pinned source URLs, commits, selected paths, licenses, corpus roles,
  and normalization/expected-output policy.
- `fixtures.lock.json` — generated-file SHA-256/byte lockfile for byte-for-byte verification.
- `../../scripts/regenerate_conformance_corpus.py` — reproducibly materializes
  raw external fixtures from the pinned commits.

Generated but gitignored files:

- `fixtures/markdownify/` — copied `python-markdownify` tests.
- `fixtures/turndown/` — copied Turndown attendant cases and JS tests.
- `fixtures/turndown-attendant/` — reference case parser/format docs.
- `fixtures/pandoc/` — selected Pandoc HTML reader/writer oracle inputs.
- `fixtures/commonmark-spec/` — CommonMark spec validation inputs.
- `fixtures/_generated_summary.json` — local count/check summary emitted by
  the regeneration script.

Regenerate from repo root:

```bash
python3 scripts/regenerate_conformance_corpus.py
```

The future phase-2 harness should consume `sources.toml` as the authoritative
manifest and treat the generated fixture files as disposable cache data.

## Differential harness

Run the correctness/fidelity differential harness from repo root after generating
fixtures:

```bash
uv run --group benchmark python tests/conformance/differential.py --report-dir tests/conformance/reports
```

The harness uses `benchmarks.harness.adapters` so performance and correctness
paths share the same converter adapter layer. It uses
`markdownify_default_oracle` as the drop-in semantic oracle, applies the
policy-level Markdown normalization from `sources.toml`, then compares each
candidate adapter output against the normalized oracle output.

Generated reports:

- `tests/conformance/reports/latest.md` — committed summary table for the latest
  staged run.
- `tests/conformance/reports/latest.json` — committed per-fixture pass/fail,
  output hashes, and bounded unified diffs for failed cases.
