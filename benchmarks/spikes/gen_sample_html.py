"""SPIKE helper (throwaway) — generate a ~5MB HTML file for the GIL-release probe.

Not the real fixture pipeline (coder-1-leaf owns big fixtures; coder-3-leaf owns
the production harness zo-1fp.2). This just gives the GIL spike something multi-MB
and structurally realistic (headings, paragraphs, links, lists, tables, nested
divs) to chew on.

Usage:
    uv run python benchmarks/spikes/gen_sample_html.py [target_mb] [out_path]
"""

import sys
from pathlib import Path

ARTICLE = """\
<article class="post" id="post-{i}">
  <header><h2>Article number {i}: a deterministic title</h2>
  <p class="byline">By Author {a} on 2026-06-{d:02d} &mdash; tags:
    <a href="/tag/alpha">alpha</a>, <a href="/tag/beta">beta &amp; gamma</a></p></header>
  <p>This is paragraph one of article {i}. It contains <strong>bold</strong>,
     <em>italic</em>, and a <a href="https://example.com/{i}">link with a
     fairly long href</a> plus some inline <code>code_{i}()</code>.</p>
  <p>Second paragraph with a nested structure to exercise the tree walker:</p>
  <div class="callout"><div class="inner"><blockquote>
    Quote inside article {i} &ndash; nested two divs deep.</blockquote></div></div>
  <ul>
    <li>list item one for {i}</li>
    <li>list item two with <a href="/x/{i}">a link</a></li>
    <li>list item three nested<ul><li>sub a</li><li>sub b</li></ul></li>
  </ul>
  <table>
    <thead><tr><th>col1</th><th>col2</th><th>col3</th></tr></thead>
    <tbody>
      <tr><td>r1c1-{i}</td><td>r1c2</td><td>r1c3</td></tr>
      <tr><td>r2c1-{i}</td><td>r2c2</td><td>r2c3</td></tr>
    </tbody>
  </table>
</article>
"""


def build(target_bytes: int) -> str:
    parts = [
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<title>GIL spike sample</title></head><body><main>",
    ]
    size = sum(len(p) for p in parts)
    i = 0
    while size < target_bytes:
        chunk = ARTICLE.format(i=i, a=i % 37, d=(i % 28) + 1)
        parts.append(chunk)
        size += len(chunk)
        i += 1
    parts.append("</main></body></html>")
    return "".join(parts)


def main() -> None:
    target_mb = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else (
        Path(__file__).parent / "sample_5mb.html"
    )
    html = build(int(target_mb * 1024 * 1024))
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html) / 1024 / 1024:.2f} MB, {html.count('<article')} articles)")


if __name__ == "__main__":
    main()
