# Canonical example

- `canonical.html` is the representative non-tricky HTML input used for manual inspection and cross-library semantic checks.
- `canonical.md` is the current html2md output for that input.

Run from the repository root:

```bash
make verify-canonical
```

The check converts `canonical.html` with html2md, markdownify, `html-to-markdown` (Rust), and Pandoc when a `pandoc` executable is installed. It renders each Markdown result back to HTML and compares normalized HTML structure, because byte-for-byte Markdown differs by convention across libraries.
