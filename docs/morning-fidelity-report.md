# Morning fidelity report prep — html2md

Snapshot basis: current main after `192b53a` (list-to-following-text blank-line fix), `af097fc` (streaming chunk-invariance fix), and `73b77a3` (lxml heading parse divergences logged). Differential command used for the snapshot:

```bash
uv run --group benchmark python tests/conformance/differential.py --report-dir /tmp/html2md-fidelity-report --max-diff-chars 300
```

## Primary markdownify-oracle gate

Primary/drop-in contract layers are `golden` and corrected `markdownify_tests` only. Guardrail corpora remain useful triangulation signals but are not the headline drop-in fidelity percentage.

| Layer / metric | html2md | html2md_streaming | Notes |
| --- | ---: | ---: | --- |
| `golden` | 64 / 64 = **100.0%** | 64 / 64 = **100.0%** | Hand-authored tricky markdownify oracle cases. |
| corrected `markdownify_tests` | 232 / 234 = **99.1% raw**, **234 / 234 = 100.0% effective** | 232 / 234 = **99.1% raw**, **234 / 234 = 100.0% effective** | Excludes custom converter fixtures; honors upstream `md(..., strip_document=None, **kwargs)`; the two raw misses are documented lxml-vs-BS4 parser divergences. |
| **Primary raw total** | 296 / 298 = **99.3%** | 296 / 298 = **99.3%** | Only the two allowed parser divergences remain raw-mismatched. |
| **Primary effective total with allowed divergences** | 298 / 298 = **100.0%** | 298 / 298 = **100.0%** | Counts the two lxml-vs-BS4 parser divergences as allowed. **Primary gate fully satisfied.** |

No unallowed primary failures remain. The two remaining raw mismatches, `markdownify:test_conversions:182` and `markdownify:test_conversions:183`, are documented allowed parser divergences. `markdownify:test_lists:47` and `markdownify:test_lists:73` are now fixed.

## Guardrail / triangulation oracles

| Guardrail layer | html2md | html2md_streaming | Notes |
| --- | ---: | ---: | --- |
| `commonmark_expected_html` | 647 / 654 = **98.9%** | 647 / 654 = **98.9%** | Uses CommonMark render-tree semantic comparison, not raw Markdown string equality. |
| `pandoc` | 7 / 8 = **87.5%** | 7 / 8 = **87.5%** | Uses Pandoc chrome/body normalization; small fixture set. |
| `turndown` | 122 / 125 = **97.6%** | 122 / 125 = **97.6%** | Default-semantics Turndown cases only. |
| `turndown_options` | 22 / 22 = **100.0%** | 22 / 22 = **100.0%** | Option-surface cases separated from default Turndown guardrail. |
| **All layers total** | 1091 / 1107 = **98.6%** | 1091 / 1107 = **98.6%** | Overall guardrail rollup; not the drop-in headline. |

## Allowed divergences

`tests/conformance/allowed_divergences.toml` currently contains five entries:

1. `golden:edge_cases:table_td_first_row_not_header` — candidate table-policy divergence: markdownify invents an empty synthetic table header for all-`td` first rows. Revisit before enabling any active allow-list for table policy.
2. `golden:edge_cases:table_colspan_and_ragged_rows` — candidate table-policy divergence: markdownify flattens colspan/ragged rows into a lossy pipe table. Revisit table raw-HTML fallback vs markdownify-compatible lossy emission.
3. `golden:edge_cases:fenced_pre_code_language_class_ignored_by_default` — candidate code-language divergence: markdownify drops language classes by default; keep default-compatible unless product chooses richer semantics.
4. `markdownify:test_conversions:182` — active primary parser divergence: lxml/browser tree construction auto-closes `<h1>` before nested `<p>` in invalid HTML; markdownify's BS4 `html.parser` keeps it nested and emits `# A P C #`.
5. `markdownify:test_conversions:183` — same active primary parser divergence as above with `heading_style=ATX`, expected by markdownify as `# A P C`.

The two `markdownify_tests` parser divergences are the only currently failing primary cases counted in the effective gate. The three golden entries are retained as policy candidates; current `golden` raw fidelity is 100%.

## Property-suite status (`zo-1fp.16`)

Validated command:

```bash
uv run --group benchmark pytest tests/property -vv
```

Result: **5 passed, 1 xfailed in 4.41s** on the latest run, within the hard <10s fast-profile requirement.

Passing relations:

- `tests/property/test_metamorphic.py::test_container_wrapping_invariance`
- `tests/property/test_metamorphic.py::test_concatenation_homomorphism`
- `tests/property/test_metamorphic.py::test_convert_stream_equivalent_to_convert_for_generated_html`
- `tests/property/test_metamorphic.py::test_fast_profile_is_default_and_bounded`
- `tests/property/test_metamorphic.py::test_html_generator_smoke`

Documented acceptable xfail:

- `tests/property/test_metamorphic.py::test_markdown_commonmark_round_trip_is_structurally_stable` — adjacent code-span delimiter textual instability. The minimized forms are CommonMark-semantically equivalent (`<p><code>0``0</code></p>`), so this is a property text-canonicalization limitation rather than a markdownify-oracle conformance gap. Disposition is documented in `docs/conformance-failure-analysis.md`.

## Gate status

**Final primary gate status: 100.0% effective fidelity** — **298 / 298** after counting the two documented lxml-vs-BS4 parser divergences. Raw primary fidelity is **296 / 298 = 99.329%**. No unallowed primary residuals remain.
