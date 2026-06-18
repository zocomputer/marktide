# Code Review: zo-1fp.11 (R1, reviewer-leaf)

- Bead: zo-1fp.11
- Commit range: 91b5d36..18dbe0b
- Plan doc: docs/design.md, docs/test-plan.md
- Reviewer: reviewer-leaf
- Review commit: 18dbe0b

## Findings

### P1 - `TagHandler.end` cannot access the element frame/data captured by `TagHandler.start`

**Location:** `src/html2md/emitter.py:105-117`, `src/html2md/rules/base.py:16-24`

**Problem**
`src/html2md/rules/base.py:16-24` defines the intended contract: `TagHandler.start` runs with the element frame on `em.state.top`, and non-local handlers should capture attributes/bookkeeping on `em.state.top.data` for use at `TagHandler.end`. However, `MarkdownEmitter.end` in `src/html2md/emitter.py:105-117` immediately pops the frame into a local variable, exposes only `em.content`, and then calls `handler.end(self)` after the popped `Frame` is no longer reachable through the handler-facing API.

That makes the documented contract unusable for the handlers being built on top of it right now: `<a>` cannot safely read the `href`/`title` it captured at start, `<img>`/`code`/`table`/`li` handlers cannot read per-element bookkeeping at end, and a workaround using state stored on the handler object would be unsafe for nested same-tag elements because handler instances are shared singletons in `TAG_HANDLERS`.

**Suggested fix**
Make the just-closed frame part of the stable end-handler contract before downstream handlers build on it. Either:

1. change the protocol to `TagHandler.end(self, em: MarkdownEmitter, frame: Frame) -> None`, or
2. expose a handler-facing property such as `em.frame` / `em.current_frame` that is valid for the duration of `handler.end` alongside `em.content`.

Add a regression test with nested same-tag elements proving each `end` sees the distinct `Frame.data` captured by its matching `start`.

---

### P1 - Streaming safe-flush/drain seam is missing, so handlers cannot implement the §4.7 contract

**Location:** `src/html2md/_threaded.py:32-43`, `src/html2md/convert.py:39-55`, `src/html2md/emitter.py:66-74`, `docs/design.md:633-641`, `docs/design.md:650-686`

**Problem**
The approved design requires true streaming: `docs/design.md:633-641` says `convert_stream` / `convert_stream_async` push safe-to-emit Markdown into a bounded queue before input EOF, and `docs/design.md:650-686` defines explicit safe-emission barriers. The foundation does not yet provide that seam. `ChunkPump.run` in `src/html2md/_threaded.py:32-43` drains nothing after each `feed` and yields only `driver.close()` at EOF; `convert_stream` in `src/html2md/convert.py:39-55` also yields only the final document; and `MarkdownEmitter` only has `emit`/`emit_text` into frame/root buffers with no committed-output buffer, `drain()`, or safe-region commit API.

This is more than a missing optimization: the rule handlers are supposed to honor §4.7 safe-flush barriers, but there is currently no stable emitter/driver API for a handler to mark output as committed and eligible to yield. Adding that later would force contract churn under the active block/inline/table handler work.

**Suggested fix**
Add the streaming commit/drain seam in the foundation before the rule tasks proceed further:

- `MarkdownEmitter` should maintain a committed-output buffer distinct from still-pending frame/root content, with an explicit handler-facing commit API or a documented rule for when closed block output becomes drainable.
- `IncrementalDriver` should expose `drain() -> str` (or equivalent) that returns committed Markdown after each `feed` without closing the parser.
- `ChunkPump` should drain after each feed and deliver committed chunks through a bounded `asyncio.Queue` / back-pressure mechanism.
- Tests should prove a completed safe block is yielded before later input/EOF, and that every yielded prefix remains a prefix of the final whole-document output.

---

### P1 - `ChunkPump.run` can call `IncrementalDriver.close` concurrently with an in-flight `IncrementalDriver.feed` on cancellation

**Location:** `src/html2md/_threaded.py:35-47`

**Problem**
`ChunkPump.run` awaits `asyncio.to_thread(driver.feed, data)` in `src/html2md/_threaded.py:35-38`. If the async generator is cancelled while that await is pending, `asyncio.to_thread` does not stop the worker-thread function; the `driver.feed` call may continue running. Control then enters the `finally` block in `src/html2md/_threaded.py:44-47`, which schedules `driver.close` on another worker thread against the same `lxml` parser.

That creates a race between `feed()` and `close()` on one `IncrementalDriver` / `etree.HTMLParser` instance. The parser is not documented as thread-safe, and this violates the design's resource-safety requirement that cancellation not leak or corrupt the worker/parser lifecycle.

**Suggested fix**
Ensure cleanup waits for any in-flight feed to finish before closing the driver, or serialize all parser operations onto one worker. For example, create an explicit task/future for each `asyncio.to_thread(driver.feed, data)`, use `asyncio.shield` so cancellation does not detach cleanup from the worker, await the in-flight feed in the cancellation path, then call `driver.close`. A single dedicated worker/queue is also acceptable if it preserves the measured loop-yield behavior.

Add a cancellation regression with a blocking/stubbed `driver.feed` that records ordering and proves `driver.close` is not invoked until the in-flight feed has exited.

---

### P2 - `escape_misc=True` does not match markdownify's escaping rules

**Location:** `src/html2md/emitter.py:37-42`, `src/html2md/emitter.py:76-86`

**Problem**
`MarkdownEmitter.escape` implements `Options.escape_misc` with a simple translation table. That does not match `markdownify==1.2.2` semantics. Markdownify escapes a regex-defined character set including backtick, tilde, equals, and pipe, and it only escapes dash/hash/list-marker sequences in context; the current table misses some characters and over-escapes `#`, `-`, and `+` everywhere.

Because `Options.escape_misc` is part of the foundation's markdownify-compatible option contract, rule handlers will inherit incorrect text escaping once conformance fixtures enable `escape_misc=True`.

**Suggested fix**
Port markdownify's `escape_misc` regex behavior exactly (including contextual dash/hash/ordered-list marker handling) into a central text-escape helper, and add unit/golden tests comparing `MarkdownEmitter.escape` / `convert` against markdownify for representative cases: backticks, `~`, `=`, `|`, ordinary hyphens, list-marker-looking `- ` / `1. ` / `1) `, and heading-looking `# ` text.

## Validation performed

- Read the foundation implementation files under `src/html2md/` and the unit tests under `tests/unit/html2md/`.
- Ran `uv run pytest tests/unit/html2md -q` → `68 passed in 0.11s`.
- Ran `uv run ruff check src/html2md tests/unit/html2md` → `All checks passed!`.
- Checked `IncrementalDriver` construction and confirmed `etree.HTMLParser(target=self.emitter, recover=True, huge_tree=True)` is set in `src/html2md/parser.py:37-39`; the unit test `tests/unit/html2md/test_parser.py:55-64` exercises an 11 MB no-truncation text node.

## Summary

4 findings: 0 P0, 3 P1, 1 P2, 0 P3

**Verdict**: Not approved

The parser construction, huge-tree setting, option-default coverage, and basic unit suite are good starts. The blocking issue is the foundation seam: active handler work needs a stable end-handler frame/data contract and a real safe-flush/drain API now, before multiple rule implementations build on a contract that cannot support non-local handlers or true streaming.
