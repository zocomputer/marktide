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

`scripts/regenerate_conformance_corpus.py` reads `sources.toml` directly as the
authoritative manifest, so source URLs, pinned commits, and selected paths cannot
drift between duplicated script constants and the manifest. The future phase-2
harness should also consume `sources.toml` as the authoritative manifest and
treat the generated fixture files as disposable cache data.

## Golden fixtures

Hand-authored golden files live in `tests/conformance/golden/*.json`. The
differential harness auto-discovers every JSON file whose `cases[]` entries have
`input_html` and `expected_markdown`, so agents can add sibling golden corpora
without editing a central registry. Normalizer-negative fixtures intentionally use
`left_markdown` / `right_markdown` and are not loaded as oracle cases.

Canonical oracle-case fields are: `id`, `behavior`, `markdownify_ref`,
`description`, `input_html`, and `expected_markdown`.

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

## Verifying the fidelity headline

Use one command from the repository root to reproduce the README fidelity claim:

```bash
make verify-fidelity
```

The command runs `tests/conformance/verify_fidelity.py` against the same layered
corpus as the differential harness, applies `tests/conformance/allowed_divergences.toml`,
and exits non-zero if the primary markdownify-oracle gate falls below 99%, if any
primary unallowed failures remain, or if `html2md_streaming` differs from one-shot
`html2md` on any corpus case.

The command leads with the primary drop-in contract. This is the fidelity claim
used by the README and release report:

- `golden`: 64/64 raw and effective.
- corrected `markdownify_tests`: 232/234 raw; 234/234 effective after the two documented
  lxml-vs-BS4 parser divergences.
- primary total (`golden` + corrected `markdownify_tests`): 296/298 raw = 99.3%;
  298/298 effective = 100.0%.

The command also prints CommonMark, Pandoc, Turndown, Turndown option-surface, and
all-layer rows as guardrail / triangulation diagnostics. Those rows compare against
other tools or spec suites with different conventions; they are intentionally not
the primary 100% drop-in fidelity claim.
