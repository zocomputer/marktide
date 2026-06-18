# zo-1fp.14 differential failure triage

Snapshot: `tests/conformance/reports/latest.json` from commit `dcba9b5` (`test: wire conformance harness to html2md`). Current live `html2md` fidelity is **313 / 1115 = 28.1%** against `markdownify_default_oracle`.

This is an interim triage while handler work is still landing. The buckets below are deliberately conservative: they identify which failures should self-resolve as handlers land, which failures need corpus/oracle normalization before they should count against the ≥99% gate, and which cases are candidates for `tests/conformance/allowed_divergences.toml` because copying markdownify may be worse than a documented intentional difference.

## Method

- Input: committed `tests/conformance/reports/latest.json`; no full corpus rerun required.
- Scope: only failed `html2md` candidate rows.
- Heuristic:
  - **Handler-not-yet-implemented** when the markdownify oracle expects concrete Markdown syntax that current `html2md` simply does not emit yet: headings, paragraph boundaries, links, images, emphasis, code fences/spans, blockquotes, lists, definition lists, tables, script/style suppression, comments/CDATA, and whitespace collapse.
  - **Normalization-needed** when the failure is from a secondary corpus whose wrapper/options/semantic equivalence should be normalized before textual oracle comparison: Pandoc template shells, CommonMark HTML→Markdown non-unique renderings, and Turndown option scenarios.
  - **Genuine divergence candidate** when the markdownify oracle behavior is a likely quirk that we may intentionally not copy. These are pre-populated in `tests/conformance/allowed_divergences.toml` as candidates, not as an active test bypass.

## Breakdown

| Layer | Failed | Handler-not-yet-implemented | Normalization-needed | Genuine divergence candidate |
| --- | ---: | ---: | ---: | ---: |
| `golden` | 54 | 51 | 0 | 3 |
| `markdownify_tests` | 171 | 171 | 0 | 0 |
| `turndown` | 103 | 77 | 26 | 0 |
| `pandoc` | 8 | 0 | 8 | 0 |
| `commonmark_expected_html` | 466 | 322 | 144 | 0 |
| **Total** | **802** | **621** | **178** | **3** |

### A. Handler-not-yet-implemented

These are expected to drop as `src/html2md` handlers land. High-signal examples:

- Paragraph/block boundaries: `tests/property/test_metamorphic.py::test_concatenation_homomorphism` xfails because `html2md.convert("<p>0</p><p>0</p>")` currently emits `00` instead of two paragraph blocks.
- Headings: `golden:block_inline_handler_cases:heading_h1_setext` loses the `=========` underline; `golden:block_inline_handler_cases:heading_h3_atx` loses the `###` marker.
- Inline formatting: `golden:block_inline_handler_cases:emphasis_em_tag` loses `*...*`; code-span delimiter cases lose backtick fences; link/image cases lose Markdown link/image syntax.
- Structural blocks: list, blockquote, definition-list, table, and pre/code cases flatten text together or drop required fences/markers.
- Ignored content: markdownify's direct tests expect comments, scripts, and styles to be suppressed; current output still needs those suppression handlers in some paths.

These should not be added to `allowed_divergences.toml` unless, after handlers land, the team explicitly chooses non-markdownify semantics.

### B. Normalization-needed

These should be normalized before declaring them real product gaps.

1. **`commonmark_expected_html` semantic normalization**
   - 144 current failures are cases where `html2md` fails and none of the three external candidates match `markdownify_default_oracle` textually.
   - Required rule: for this layer, add a secondary assertion that renders both oracle and candidate Markdown through a CommonMark parser and compares normalized HTML trees. Markdown is not unique; textual inequality should not automatically fail a CommonMark-derived HTML fixture.
   - Guardrail: keep the existing normalizer negative cases so semantic normalization never hides link target/title changes, image alt/src changes, list nesting changes, code-block content changes, or table column changes.

2. **`pandoc` fixture normalization**
   - All 8 Pandoc cases currently fail. The full-document S5/Pandoc fixtures include template CSS, metadata shells, repeated title blocks, and generated wrapper structure that are not stable Markdown-conversion semantics.
   - Required rule: add a `pandoc_to_canonical` fixture transform before oracle conversion that extracts the relevant body/content region, drops generated `<style>`/presentation chrome, and records which Pandoc fixtures are intentionally fixture-smoke-only versus default-fidelity gates.
   - The current `pandoc` 0/8 should not be interpreted as eight independent handler bugs.

3. **`turndown` option-surface normalization**
   - 21 of the 103 failing Turndown cases carry `data-options` such as `headingStyle`, `linkStyle`, `codeBlockStyle`, `fence`, `bulletListMarker`, and `preformattedCode`.
   - Required rule: separate default-semantics Turndown fixture cases from option-surface cases. Option cases should become option-mapping tests only after the corresponding `html2md.Options` field exists; until then they should be reported separately from the default ≥99% markdownify gate.
   - The remaining secondary Turndown failures overlap heavily with handler gaps (links, images, code, lists, tables) and should shrink as handlers land.

### C. Genuine divergence candidates

`tests/conformance/allowed_divergences.toml` is now pre-populated with three candidate entries:

1. `golden:edge_cases:table_td_first_row_not_header` — markdownify invents an empty synthetic header for a table whose first row contains only `<td>` cells.
2. `golden:edge_cases:table_colspan_and_ragged_rows` — markdownify flattens colspan/ragged rows into a lossy pipe table.
3. `golden:edge_cases:fenced_pre_code_language_class_ignored_by_default` — markdownify drops `class="language-python"` instead of preserving it as a fence info string.

These are **not active bypasses**. They are decision points to re-review with coder-3/table and coder-2/block-inline owners before the differential gate reads `allowed_divergences.toml`.

## Next mechanical path to ≥99%

1. Let block/inline/table handlers land.
2. Re-run `uv run --group benchmark python tests/conformance/differential.py --report-dir tests/conformance/reports --max-diff-chars 2000` once per meaningful handler landing, not in a tight loop.
3. Recompute this triage: handler bucket should collapse first.
4. Implement the CommonMark/Pandoc/Turndown normalization rules above and move those cases out of raw textual-fidelity accounting.
5. Promote, reject, or delete the candidate divergences before enabling an active allow-list in the differential gate.

## Harness-side normalization implementation update

Commit after this triage implements the converter-independent harness normalization items:

- `tests/conformance/differential.py::commonmark_semantic_equal` renders `commonmark_expected_html` oracle/candidate Markdown with `markdown_it.MarkdownIt("commonmark")` and compares canonicalized HTML fragments instead of raw Markdown strings.
- `tests/conformance/differential.py::strip_pandoc_chrome` removes Pandoc template chrome (`head`, `style`, `script`, `meta`, `link`, `title`) before both oracle and candidate conversion for the `pandoc` layer.
- `tests/conformance/differential.py::load_turndown_cases` separates option-surface fixtures into the `turndown_options` layer so default Turndown triangulation is not conflated with unmapped option behavior.
- `tests/conformance/differential.py::summarize` now reports primary markdownify-oracle fidelity over only `golden` + `markdownify_tests`; CommonMark, Pandoc, Turndown, and Turndown options remain guardrail/triangulation layers.

Post-normalizer snapshot from `tests/conformance/reports/latest.json`: primary `html2md` fidelity is **257 / 306 = 84.0%**; overall guardrail total is **947 / 1115 = 84.9%**. This snapshot includes handler work present in the shared working tree at the time of the run; the durable harness change is the normalization and primary/guardrail accounting, not the exact handler-pass count.

## Markdownify unit-test oracle correction

`tests/conformance/differential.py::load_markdownify_cases` now mirrors the upstream `tests/utils.py::md` helper instead of treating those fixtures as default-option conversions:

- `test_custom_converter.py` is excluded because it exercises a custom `MarkdownConverter` subclass, not default/drop-in behavior.
- Per-assert keyword arguments are captured from the `md(...)` AST call and stored in `Case.metadata["markdownify_options"]`.
- The implicit upstream helper default `strip_document=None` is applied per markdownify-test case.
- `tests/conformance/differential.py::_candidate_output` applies those options to local `html2md`/`html2md_streaming` via `html2md.options.markdownify_compat`.
- `tests/conformance/differential.py::_oracle_output` uses the upstream expected string as the oracle for this layer, so option-specific tests are measured against the behavior they actually assert.

Corrected fast primary snapshot after block/inline + table handler landings: primary `html2md` fidelity is **229 / 298 = 76.8%** across `golden` + corrected `markdownify_tests`; the corrected `markdownify_tests` sublayer alone is **173 / 234 = 73.9%**. `html2md_streaming` matches the same numbers.
