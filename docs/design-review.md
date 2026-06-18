# Review: `docs/design.md` / `docs/test-plan.md` (`reviewer-leaf`)

- Source docs: `docs/design.md`, `docs/test-plan.md`
- Reviewed commit: `445bae8` (`docs(html2md): fold coder-3-leaf GIL/streaming spike into design go/no-go`)
- Reviewer: `reviewer-leaf`
- Bead: `zo-1fp.1`

## Findings

### P1 - Normalization and secondary-corpus transforms are named but not specified enough to implement safely

**Problem**

`docs/design.md:500` through `docs/design.md:505` correctly names `markdownify==1.2.2` as the single primary oracle, and `docs/design.md:520` through `docs/design.md:523` correctly says Turndown/CommonMark/Pandoc must not be mixed into primary assertions raw. However, the actual normalization contract remains too vague for an implementer to write without inventing behavior. `docs/design.md:525` through `docs/design.md:533` says Turndown uses a "Turndown→markdownify transform" and Pandoc uses a "Pandoc→canonical transform", but only gives examples like heading/emphasis/`<br>` conversion. `docs/design.md:562` through `docs/design.md:568` then says normalization will collapse blank lines, normalize list markers/indent, trim trailing whitespace, and normalize link style before asserting semantic equivalence. `docs/test-plan.md:84` through `docs/test-plan.md:88` makes that normalizer gating for the drop-in oracle, with divergences recorded only after normalization.

That is dangerous because these transforms can easily hide real regressions: list indentation is semantic in Markdown; blank lines can change list/code/table parsing; escaping changes can alter emitted text; link normalization can mask URL/title bugs. The plan says the normalizer is unit-tested at `docs/test-plan.md:101` through `docs/test-plan.md:105`, but it does not define the normalizer's input/output rules, invariants, or fixture examples tightly enough to test.

**Required fix**

Add a concrete normalization specification before implementation:

- Define the exact Markdown normalizer operations in order, with examples of before/after and a list of operations it must never perform.
- Define `turndown_to_markdownify` and `pandoc_to_canonical` as named transform functions with exact rules and explicit non-goals.
- Add a schema for `e2etests/differential/allowed_divergences.toml` that records source corpus, case id, normalized diff summary, reason, owner, and expiry/revisit condition.
- Add normalizer negative tests that prove it does **not** erase semantic differences in nested lists, code blocks, tables, link targets/titles, image alt text, and escaped punctuation.

---

### P1 - `Options` does not actually track `markdownify==1.2.2` defaults or option surface despite the drop-in compatibility claim

**Problem**

The plan states that `html2md` is a drop-in replacement for `markdownify` at `docs/design.md:3` through `docs/design.md:6`, that the `Options` surface mirrors `markdownify` at `docs/design.md:58` through `docs/design.md:60`, and that defaults track `markdownify==1.2.2` at `docs/design.md:507` through `docs/design.md:518`. But the proposed `Options` dataclass in `docs/design.md:604` through `docs/design.md:624` already diverges from `markdownify.MarkdownConverter.DefaultOptions` in ways that will affect output:

- `docs/design.md:611` uses `bullet: str = "-"`, while `markdownify` defaults to `bullets = '*+-'` and chooses nested unordered-list markers by depth.
- `docs/design.md:619` uses `escape_misc: bool = True`, while `markdownify` defaults `escape_misc = False` and separately defaults `escape_asterisks = True` and `escape_underscores = True`.
- `docs/design.md:620` and `docs/design.md:621` define `strip_tags` / `drop_tags`, but `markdownify` exposes mutually exclusive `strip` / `convert` semantics; these are not equivalent.
- The dataclass omits or defers important compatibility knobs such as `keep_inline_images_in`, `default_title`, `table_infer_header`, `strip_document`, `strip_pre`, `code_language`, `code_language_callback`, `sub_symbol`, `sup_symbol`, and wrapping semantics.

The plan acknowledges uncertainty at `docs/design.md:811`, but this is not an implementation detail: option compatibility determines the oracle, fixture expectations, adapter normalization, and public API migration path.

**Required fix**

Before implementation, decide the compatibility target and encode it precisely:

- If this is truly drop-in compatible, make `Options` a faithful typed representation of all `markdownify==1.2.2` options, including exact defaults and the `strip`/`convert` mutual exclusion.
- If only a subset is supported, remove the "drop-in" wording and define the exact subset plus required migration behavior for unsupported kwargs.
- Add an `Options.from_markdownify_kwargs(...)` / `markdownify_compat(...)` contract with acceptance and rejection behavior for every `markdownify==1.2.2` option.
- Update `docs/design.md:168` through `docs/design.md:185` so apples-to-apples benchmark option mapping references this exact option contract, not an approximate prose list.

---

### P1 - Streaming emission safety is asserted, but the design does not define when output is safe to yield under markdownify-compatible whitespace/list/table rules

**Problem**

The design promises true streaming output at `docs/design.md:480` through `docs/design.md:487`, says most rules are local at `docs/design.md:438` through `docs/design.md:439`, and relies on a small `pending inline buffer` at `docs/design.md:420` through `docs/design.md:421`. But markdownify-compatible output is not purely local: the plan itself identifies whitespace boundary trimming from `markdownify.MarkdownConverter.process_tag` and `markdownify.MarkdownConverter.process_text` as part of the contract at `docs/design.md:515` through `docs/design.md:518`, and table output is explicitly buffered until `</table>` at `docs/design.md:417` through `docs/design.md:419`.

For a public `convert_stream(...) -> Iterator[str]` / `convert_stream_async(...) -> AsyncIterator[str]` API, once a chunk has been yielded it cannot be rewritten. The plan does not specify "safe emission barriers" for paragraphs, nested lists, blockquotes, table rows, inline whitespace, or pending links/images. Without those barriers, an implementation can pass many tag-local tests and still fail `convert_stream(split) == convert(whole)` when future siblings determine whether whitespace/newlines should be stripped or collapsed.

**Required fix**

Add a streaming emission contract:

- Define exactly when each block type may flush output: paragraph, heading, list item, nested list, blockquote, pre/code, table, div/section/article, and document close.
- Define what state is retained between flushes, including trailing whitespace/newline state and parent/previous-sibling context needed to reproduce markdownify boundary trimming.
- State whether `convert_stream` may buffer an entire current block/table/list subtree before yielding, and define worst-case memory for huge single blocks.
- Add tests that assert early-yield behavior without compromising byte equality: for selected fixtures, record the sequence of yielded chunks and assert no yielded prefix later needs mutation.

---

### P1 - GIL/event-loop claims still risk overclaiming because callback-heavy chunks can hold the GIL for unbounded Python work within one `parser.feed(...)`

**Problem**

The stage decomposition at `docs/design.md:288` through `docs/design.md:307` is a strong improvement: it separates parse-only, parse+iteration, and full conversion. The calibration controls at `docs/design.md:309` through `docs/design.md:322` are also appropriate. However, the phase-2 design still makes a structural claim that is not guaranteed by the described implementation: `docs/design.md:401` through `docs/design.md:403` says contiguous GIL-hold is bounded by one chunk's callbacks, and `docs/design.md:480` through `docs/design.md:482` says the event loop stays responsive because lxml releases the GIL during each `feed()`.

That bound is too weak and may be false for adversarial HTML. A 64 KiB chunk can contain thousands of tiny tags, entities, or table cells, causing many Python `MarkdownEmitter.start`, `MarkdownEmitter.data`, and `MarkdownEmitter.end` callbacks inside a single `parser.feed(...)` call. Those callbacks run with the GIL held, and the plan does not include a callback budget, cooperative yield point, or dynamic chunk-size adjustment based on observed callback density. A small byte chunk is not necessarily a small Python-work chunk.

**Required fix**

Strengthen the design and probe so the claim is falsifiable for callback-heavy input:

- Add synthetic callback-density fixtures to `benchmarks/harness/synth.py` and the GIL proof suite: thousands of empty tags, deeply nested tags, many small table cells, entity-heavy text, and link/image storms within one chunk.
- Report event count per chunk, max callbacks per `feed()`, max `feed()` wall time, and heartbeat delay alongside byte chunk size.
- Define an acceptance bound for max per-feed wall time / heartbeat p99 on callback-heavy fixtures.
- If the Python target parser cannot meet the bound, specify the fallback design: smaller adaptive chunks, a pull-parser loop with explicit yield checkpoints, or a native emitter.

---

### P1 - Acceptance thresholds are placeholders, so phase-1/phase-3 gates are not actionable

**Problem**

The plan correctly identifies phase-1 and phase-3 gates, but the numeric criteria remain placeholders. `docs/design.md:344` through `docs/design.md:348` uses examples such as `≥ 5×` and `≤ 10 ms`, then `docs/design.md:350` through `docs/design.md:352` says thresholds are placeholders to be fixed later. `docs/design.md:707` through `docs/design.md:714` likewise uses `target×`, `≤ bound`, and `target%` for final acceptance. `docs/test-plan.md:172` through `docs/test-plan.md:175`, `docs/test-plan.md:135` through `docs/test-plan.md:139`, and `docs/test-plan.md:160` through `docs/test-plan.md:161` refer to bounds/tolerances without giving values.

Because this review gates implementation, leaving the pass/fail gates open means different agents can implement the harness, evaluate candidates, and decide whether phase 2 is needed using different unstated thresholds.

**Required fix**

Before phase-1 implementation starts, set explicit initial gates in the plan:

- Throughput target by fixture tier.
- Worker-thread heartbeat p95/p99/max bounds by fixture tier and by CI smoke vs full benchmark.
- Peak RSS bound for one-shot and streaming paths.
- Semantic match threshold and divergence-budget rules.
- Perf regression tolerance and baseline update procedure.

These can be revised after first measurements, but the initial gate must be concrete and versioned in `docs/design.md` so the phase-1 result is not a judgment call.

---


### P2 - Phase-2 justification does not gate time-to-first-output even though a loop-friendly one-shot Rust baseline exists

**Problem**

`docs/rust-candidate-smoke.md:51` through `docs/rust-candidate-smoke.md:78` shows the important nuance for the phase-1 decision: all three Rust candidates are one-shot/no-streaming APIs; `html2text_rs==0.2.5` is loop-friendly under `asyncio.to_thread`, but lower fidelity and still whole-string `str -> str`. The design has good streaming motivations in `docs/design.md:47` through `docs/design.md:50` and `docs/design.md:480` through `docs/design.md:487`, and the new spike framing in `docs/design.md:187` through `docs/design.md:223` explicitly distinguishes async-friendliness, bounded memory, and time-to-first-output. However, the phase-1/phase-3 gates at `docs/design.md:339` through `docs/design.md:352` and `docs/design.md:707` through `docs/design.md:716` still do not include any explicit time-to-first-output or streaming-latency metric.

That leaves the build-vs-adopt decision overly centered on async heartbeat, throughput, memory, and final output quality. Since `html2text_rs==0.2.5` demonstrates that an existing one-shot Rust library can be event-loop-friendly, the design should make the additional streaming value falsifiable: bounded peak RSS for huge inputs and early output before the full input is read. Peak RSS is present; time-to-first-output is not.

**Required fix**

Add streaming-specific metrics and gates to phase 1/3:

- Time to first Markdown chunk for `convert_stream` / `convert_stream_async` on large fixtures.
- Output cadence / max gap between emitted chunks for long documents with many completed blocks.
- First-output and cadence comparison against one-shot libraries, which necessarily emit only after full conversion.
- A clear rule that phase 2 is justified if no candidate satisfies the combined quality + memory + time-to-first-output requirements, even if one candidate is loop-friendly.

---

### P2 - Benchmark fixture reproducibility is still delegated to mutable live downloads

**Problem**

`docs/design.md:225` through `docs/design.md:245` relies on the generated fixtures from `docs/research.md`, and `docs/test-plan.md:253` through `docs/test-plan.md:257` says large fixtures are regenerated by the pinned command. But the design doc does not incorporate the necessary manifest/hashing correction: the current research generator downloads live pages and byte-truncates assembled HTML. This can change over time and can accidentally create malformed fixtures that are not labeled as malformed.

This is especially important because `docs/design.md:336` through `docs/design.md:337` and `docs/test-plan.md:154` through `docs/test-plan.md:156` rely on output hashes and fixed input bytes for fair performance comparison.

**Required fix**

Add a benchmark fixture manifest requirement to `docs/design.md` / `docs/test-plan.md`:

- `benchmarks/fixtures/manifest.json` records source URL, retrieval timestamp, response hash, source byte count, generator version, target size, output hash, and whether truncation/malformedness is intentional.
- Safe-boundary fixtures and intentionally malformed truncated fixtures are separate named cases.
- Nightly/on-demand jobs verify fixture hashes before benchmarking and fail with a clear regeneration instruction if they differ.

---

### P2 - The optional `ConversionResult` / `convert_detailed(...)` API is unresolved scope in a public-interface section

**Problem**

`docs/design.md:596` through `docs/design.md:602` introduces an optional `ConversionResult` / `convert_detailed(...)` API for parity with the Rust candidate, then defers the decision to implementation. This adds public API uncertainty to a design that otherwise says the deliverable is a `markdownify` drop-in string-returning converter. It also has no consumer in the plan, no tests in `docs/design.md:677` through `docs/design.md:715`, and no black-box coverage in `docs/test-plan.md:51` through `docs/test-plan.md:72`.

**Required fix**

Either remove `ConversionResult` / `convert_detailed(...)` from the implementation plan, or make it a concrete committed public API with fields, error/warning semantics, and tests. Do not leave it as an implementation-time choice.

---

### P2 - Some test commitments lack concrete assertion values or artifact schemas

**Problem**

The test plan generally does a good job listing paths, runners, cadence, and artifacts. However, several tests still specify qualitative assertions without concrete values or artifact schemas:

- `docs/test-plan.md:172` through `docs/test-plan.md:175` says load p99 heartbeat delay stays under bound, but no bound is given.
- `docs/test-plan.md:176` through `docs/test-plan.md:179` says RSS slope is approximately zero, but no slope/tolerance/window is defined.
- `docs/test-plan.md:183` through `docs/test-plan.md:185` names `e2etests/results/load.json` and plots, but not the fields required for future regression comparison.
- `docs/test-plan.md:216` through `docs/test-plan.md:217` says minimized repros are committed under `e2etests/fuzz/repros/` when failures are found, but does not define naming/provenance metadata for those repros.

**Required fix**

Add a small "artifact schemas and thresholds" section to `docs/test-plan.md` defining the required JSON fields and numeric pass/fail tolerances for heartbeat, RSS slope, queue depth, timeout, and fuzz repro metadata.

---

## Summary

8 findings: 0 P0, 5 P1, 3 P2, 0 P3

**Verdict**: Not approved for implementation until the P1 findings are incorporated. The overall architecture is promising, and the docs hit the major required themes, but the oracle/normalizer, option compatibility, streaming flush safety, GIL bound, and numeric gates need to be made concrete before parallel implementation starts.
