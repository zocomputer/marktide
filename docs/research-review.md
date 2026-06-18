# Review: `docs/research.md`

Date: 2026-06-18  
Reviewer: `reviewer-leaf`  
Reviewed commit: `ecb2407` (`docs: research html markdown benchmark inputs`)  
Reviewed bead: `zo-1fp.3`

## Verdict

The package shortlist is directionally useful, and the `html-to-markdown==3.5.7` pin is sound under the 7-day supply-chain cooldown. However, `docs/research.md` is not yet strong enough for the downstream design/benchmark work because it does not mechanically pin external conformance corpora, does not actually assess streaming support for each candidate, and does not define apples-to-apples option settings for semantic/performance comparisons.

## Positive checks

- `docs/research.md:11` and `docs/research.md:12` correctly avoid `html-to-markdown==3.6.13` because PyPI shows the `html_to_markdown-3.6.13` files were uploaded on 2026-06-17, inside the 7-day cooldown window.
- `docs/research.md:12` and `docs/research.md:47` correctly identify `html-to-markdown==3.5.7` as old enough: PyPI shows `html_to_markdown-3.5.7` files uploaded on 2026-05-29.
- The local package installations described at `docs/research.md:33`, `docs/research.md:57`, and `docs/research.md:77` are plausible and match the local `.venv`: `html-to-markdown==3.5.7`, `htmd-py==0.1.2`, and `html2text_rs==0.2.5` are installed and importable.
- The local metadata confirms acceptable candidate licenses even though the research doc does not record them: `html-to-markdown==3.5.7` has `License-Expression: MIT`, `htmd-py==0.1.2` has `License :: OSI Approved :: Apache Software License`, and `html2text_rs==0.2.5` has `License: MIT License`.

## Findings

### P1 — External conformance corpora are not reproducibly pinned or mechanically imported

`docs/research.md:189`, `docs/research.md:206`, `docs/research.md:207`, `docs/research.md:226`, and `docs/research.md:242` all use `git clone --depth 1` from moving default branches into `/tmp`. `docs/research.md:195` then says to "Import or translate individual test vectors", and `docs/research.md:215` says to put "normalized converted cases" under `tests/conformance/turndown_cases/`. This leaves the eventual conformance suite vulnerable to drifting upstream test contents and manual cherry-picking.

For this project, the research doc should specify a manifest-driven pull strategy now, not defer it to `docs/research.md:275`. The manifest should include exact repository URL, commit SHA, source path(s), fixture parser/transform, expected-output transform, license, and generated case count for at least `matthewwithanm/python-markdownify`, `mixmark-io/turndown`, `mixmark-io/turndown-attendant`, `jgm/pandoc`, and `commonmark/commonmark-spec` if those remain in scope.

### P1 — Candidate streaming support is not actually assessed

The assignment asked whether candidate libraries can replace or avoid building a streaming converter. `docs/research.md:268` only says the future benchmark should record whether conversion is whole-document-only or can stream/chunk; it does not answer that question for `html-to-markdown==3.5.7`, `htmd-py==0.1.2`, or `html2text_rs==0.2.5`. The APIs recorded at `docs/research.md:41`, `docs/research.md:63`, and `docs/research.md:83` are all whole-string calls, but the doc does not explicitly classify them as whole-document APIs, identify any lower-level incremental parser APIs, or state whether chunked input/output is unsupported.

The research doc should add a per-candidate row for streaming capability: input type, output type, incremental parse support, incremental emit support, backpressure/callback support, and whether chunk-boundary-equivalent conversion can be tested. Without that, phase 1 can benchmark speed but cannot make the key build-vs-adopt decision.

### P1 — Apples-to-apples option mapping is missing

`docs/research.md:254` through `docs/research.md:261` lists default API calls, but it does not define common options for headings, bullet markers, emphasis markers, escaping, wrapping, hard-break style, metadata extraction, preprocessing, image handling, and table formatting. This matters because local inspection of `html_to_markdown.ConversionOptions` shows defaults such as `heading_style='atx'`, `escape_asterisks=False`, `escape_underscores=False`, `extract_metadata=True`, and `preprocessing` behavior, while `markdownify.MarkdownConverter.DefaultOptions` in `/Users/dcosson/h2home/projects/new-html-parser/.venv/lib/python3.12/site-packages/markdownify/__init__.py:176` defaults to underlined h1/h2, asterisk emphasis, escaping asterisks/underscores, and no metadata extraction.

The benchmark and semantic sample at `docs/research.md:263` through `docs/research.md:269` should define two modes: (1) package-default comparison, clearly labeled as end-user default behavior, and (2) normalized comparison with explicit options that minimize intentional semantic/style differences. Otherwise throughput and preservation scores will be confounded by unequal work.

### P2 — License and maintenance checks are incomplete in the checked-in research

The research doc links package and repository pages at `docs/research.md:27`, `docs/research.md:52`, `docs/research.md:73`, and `docs/research.md:93`, but it does not record license, latest release date, repository pushed-at date, wheel platform coverage, or whether the Python wheel is available on the likely CI/prod platforms. I verified current repository metadata via the GitHub API: `kreuzberg-dev/html-to-markdown` is MIT and recently pushed on 2026-06-17, `lmmx/htmd` is Apache-2.0 and pushed on 2026-06-15, `letmutex/htmd` is Apache-2.0 and pushed on 2026-04-04, and `deedy5/html2text_rs` is MIT and pushed on 2026-04-23.

Those checks should be in `docs/research.md`, because downstream implementers should not have to rediscover whether a dependency is legally acceptable and maintained.

### P2 — Benchmark fixture generation is mutable and can produce malformed truncation artifacts

The generator at `docs/research.md:129` through `docs/research.md:142` downloads live pages without recording response hashes, ETags, archival URLs, or retrieval timestamps in a machine-readable manifest. The slicing at `docs/research.md:162` truncates the fully assembled byte string to the target size, which can cut through a UTF-8 sequence, HTML tag, attribute, entity, table, or code block. It also prevents the intended suffix at `docs/research.md:159` from being guaranteed present. Some malformed fixtures are useful, but the current doc accidentally makes every target-size fixture potentially malformed and non-reproducible.

The benchmark fixture plan should write a `benchmarks/fixtures/manifest.json` with source URL, retrieval timestamp, SHA-256, source byte count, target byte count, generation algorithm version, and output SHA-256. It should either truncate only at safe boundaries or explicitly create separate `malformed_truncated_*` fixtures so malformed-input behavior is measured intentionally.

## Supply-chain pin conclusion

The `html-to-markdown==3.5.7` choice over `html-to-markdown==3.6.13` is sound. As of this review on 2026-06-18, PyPI reports `3.6.13` uploaded on 2026-06-17 and `3.5.7` uploaded on 2026-05-29, so `3.5.7` satisfies a 7-day cooldown while preserving the modern `convert()` / `ConversionResult` API used by the planned benchmark.
