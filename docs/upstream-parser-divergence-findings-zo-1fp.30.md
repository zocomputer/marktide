# zo-1fp.30 upstream parser-divergence filing analysis

Status: **do not post any public issue without user approval**.

This note investigates whether the two documented parser divergences should be
filed upstream. The bar here is intentionally high: only file if we can show a
real upstream defect rather than known/documented parser behavior or invalid HTML
where implementations are allowed or expected to differ.

## Sources checked

Official/spec sources:

- WHATWG HTML parsing parse errors: `cdata-in-html-content` says CDATA outside
  SVG/MathML foreign content is a parse error and is treated as a comment.
  <https://html.spec.whatwg.org/multipage/parsing.html#parse-errors>
- WHATWG HTML tokenizer markup declaration rule: `<![CDATA[` in the HTML
  namespace creates a comment token with data `[CDATA[` and switches to bogus
  comment state. <https://html.spec.whatwg.org/multipage/parsing.html#markup-declaration-open-state>
- WHATWG HTML `CDATA section state`: real CDATA character-token behavior is only
  reached when the adjusted current node is not in the HTML namespace.
  <https://html.spec.whatwg.org/multipage/parsing.html#cdata-section-state>
- WHATWG `h1`-`h6` element definition: heading elements permit **phrasing
  content** only. <https://html.spec.whatwg.org/multipage/sections.html#the-h1,-h2,-h3,-h4,-h5,-and-h6-elements>
- WHATWG `in body` tree-construction rules: a `<p>` start tag is inserted as an
  HTML element; the rule does not say to close an open heading element first.
  <https://html.spec.whatwg.org/multipage/parsing.html#parsing-main-inbody>
- Beautiful Soup parser docs: Beautiful Soup documents that different parsers
  produce different trees for invalid markup, and that `html5lib` parses the way
  browsers do / uses HTML5-standard techniques. <https://www.crummy.com/software/BeautifulSoup/bs4/doc/#differences-between-parsers>
- libxml2 HTML parser docs: the HTML parser "doesn't support HTML5" as a full
  parser; as of 2.14 the tokenizer conforms to HTML5, but tree construction is a
  custom unspecified algorithm with many differences to HTML5.
  <https://gnome.pages.gitlab.gnome.org/libxml2/html/HTMLparser_8h.html>

Issue-tracker/web checks:

- Existing libxml2 issue: "HTML5 support (#211)" already covers the broad class
  that libxml2's HTML parser does not implement HTML5 tree construction.
  <https://gitlab.gnome.org/GNOME/libxml2/-/issues/211>
- Search did not find a narrower existing lxml/libxml2 issue specifically for
  `foo <![CDATA[>&<]]>`; that is expected because the observed behavior matches
  HTML5 tokenization for HTML-namespace CDATA-like text.

## Local reproductions

Environment used for sanity checks:

```text
lxml 6.1.1; libxml2 2.14.6
```

### Nested block inside heading

Input:

```html
<h1>A <p>P</p> C </h1>
```

Observed parse shapes:

```text
BeautifulSoup(..., "html.parser"): <h1>A <p>P</p> C </h1>
BeautifulSoup(..., "html5lib"):     <html><head></head><body><h1>A <p>P</p> C </h1></body></html>
BeautifulSoup(..., "lxml"):         <html><body><h1>A </h1><p>P</p> C </body></html>
lxml.html.fromstring(...):           <div><h1>A </h1><p>P</p> C </div>
```

Conclusion from reproduction + spec:

- The source is **non-conforming HTML** because `h1` permits phrasing content,
  and `p` is not phrasing content.
- However, the HTML5 tree-construction algorithm does **not** auto-close an open
  heading when a `p` start tag appears. `html5lib` agrees with
  BeautifulSoup/`html.parser` on this specific tree shape.
- Therefore our earlier shorthand "lxml/browser-correct" for this case is too
  strong. More precise wording: **the case is invalid HTML; markdownify's
  BeautifulSoup/html.parser behavior happens to match html5lib/HTML5 tree
  construction for this invalid input; lxml/libxml2 differs because its HTML tree
  builder is documented as non-HTML5/custom.**

Recommendation: **do not file a Beautiful Soup or markdownify bug.** There is no
basis to claim BeautifulSoup/`html.parser` is out of spec for this specific tree
shape. Also **do not file a new lxml/libxml2 bug by default**: the difference is
covered by libxml2's documented non-HTML5 tree-construction limitation and the
existing broad HTML5 support issue. A narrow upstream issue would likely be
noise unless the user specifically wants to advocate for one more example under
that existing umbrella.

Project follow-up recommendation: update internal divergence wording that calls
lxml/browser behavior "browser-correct" for `markdownify:test_conversions:182`
and `markdownify:test_conversions:183`. The filing recommendation remains
"don't file" either way.

## CDATA-like text in HTML content

Input:

```html
foo <![CDATA[>&<]]>
```

Observed parse shapes/events:

```text
BeautifulSoup(..., "html.parser"): foo <![CDATA[>&<]]>
BeautifulSoup(..., "html5lib"):     <html><head></head><body>foo <!--[CDATA[-->&amp;&lt;]]&gt;</body></html>
BeautifulSoup(..., "lxml"):         <html><body>foo <!--[CDATA[-->&amp;&lt;]]&gt;</body></html>
lxml target events:                  data 'foo ', comment '[CDATA[', data '&', data '<', data ']]>'
```

Conclusion from reproduction + spec:

- In ordinary HTML content, `<![CDATA[` is not a real CDATA section. The WHATWG
  tokenizer treats it as `cdata-in-html-content`, creates a comment token with
  data `[CDATA[`, and enters bogus comment state.
- For `<![CDATA[>&<]]>`, the `>` immediately after `[CDATA[` ends the bogus
  comment, so the following `&<]]>` is ordinary text (serialized as
  `&amp;&lt;]]&gt;`).
- `html5lib` and lxml/libxml2 agree on this behavior. BeautifulSoup/`html.parser`
  preserves the CDATA-like source text, which is useful for markdownify's oracle
  but not HTML5 tokenization.
- libxml2's official docs say its tokenizer conforms to HTML5 as of 2.14, and
  this specific behavior is consistent with that tokenizer rule.

Recommendation: **do not file an lxml/libxml2 bug.** The current lxml/libxml2
behavior appears spec-correct for HTML-namespace input. Also **do not file a
Beautiful Soup bug**: `html.parser` preservation is parser-specific behavior that
Beautiful Soup already documents under parser differences for invalid markup.

Project follow-up recommendation: keep `commonmark:0630` as a documented
non-primary/guardrail divergence if html2md intentionally parses HTML rather than
source-preserving CommonMark raw HTML. Do not describe it as lxml dropping valid
HTML CDATA; it is HTML-namespace CDATA-like text that HTML5 tokenizes as a
comment plus text.

## Overall filing recommendation

| Case | Upstream target considered | Recommendation | Rationale |
| --- | --- | --- | --- |
| `markdownify:test_conversions:182` / `183` (`<h1>A <p>P</p> C </h1>`) | Beautiful Soup / markdownify | **Do not file** | Input is non-conforming, but BeautifulSoup/html.parser is not out-of-spec here; html5lib matches its tree shape. |
| same nested-heading case | lxml / libxml2 | **Do not file by default** | lxml/libxml2 differs from HTML5 here, but libxml2 explicitly documents custom non-HTML5 tree construction and already has a broad HTML5-support tracker. |
| `commonmark:0630` (`foo <![CDATA[>&<]]>`) | lxml / libxml2 | **Do not file** | lxml/libxml2 behavior matches WHATWG HTML tokenization for CDATA-like text outside foreign content. |
| same CDATA-like case | Beautiful Soup / markdownify | **Do not file** | Parser-specific source preservation; Beautiful Soup documents parser differences for invalid/non-perfect markup. |

No public issue draft is included because the recommendation for every case is
**do not file** absent an explicit user decision to file a low-priority example
against libxml2's already-known HTML5 tree-construction gap.
