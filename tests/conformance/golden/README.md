# Hand-authored conformance golden data

This directory contains small, reviewed data fixtures that complement the imported
external corpora under `tests/conformance/fixtures/`.

- `edge_cases.json` covers the required tricky-fidelity areas from
  `docs/design.md` §5.3.4. Each case has hand-authored `input_html` and the
  `expected_markdown` produced by the markdownify default oracle.
- `block_inline_handler_cases.json` is the exhaustive per-handler acceptance set for the
  block + inline tag groups (`p`, `h1`–`h6`, `blockquote`, `hr`, `ul`/`ol`/`li`,
  `strong`/`em`, code spans, `br`, `span`) — same schema as `edge_cases.json`, picked up by
  the same `*.json` glob loader. Regenerate with `_generate_golden.py` (oracle-generated, no
  hand-transcription; the script asserts `markdownify==1.2.2`).
- `normalizer_negative_cases.json` covers `docs/design.md` §5.3.5. Each
  `left_markdown` / `right_markdown` pair must remain different after the future
  `normalize_md` implementation; equality means the normalizer is masking a real
  regression.

These are pure data fixtures. They intentionally do not import or depend on the
future `marktide` converter. Phase-2 wiring should load them into the conformance
suite once the normalizer and converter modules exist.
