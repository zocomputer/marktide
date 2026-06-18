# Conformance differential report

Full per-fixture JSON: `/Users/dcosson/h2home/projects/new-html-parser/tests/conformance/reports/latest.json`

Case count: `1107`

## Primary markdownify-oracle fidelity

Primary layers: `golden`, `markdownify_tests`

| Adapter | Passed | Failed | Errors | Fidelity |
| --- | ---: | ---: | ---: | ---: |
| `htmd_py` | 137 | 161 | 0 | 46.0% |
| `html2md` | 294 | 4 | 0 | 98.7% |
| `html2md_streaming` | 294 | 4 | 0 | 98.7% |
| `html2text_rs` | 116 | 182 | 0 | 38.9% |
| `html_to_markdown` | 163 | 135 | 0 | 54.7% |
| `lxml_naive` | 67 | 229 | 2 | 22.5% |

## Totals by adapter

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 769 | 338 | 0 |
| `html2md` | 1091 | 16 | 0 |
| `html2md_streaming` | 1091 | 16 | 0 |
| `html2text_rs` | 584 | 523 | 0 |
| `html_to_markdown` | 726 | 381 | 0 |
| `lxml_naive` | 354 | 749 | 4 |

## Totals by layer

### `commonmark_expected_html`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 544 | 110 | 0 |
| `html2md` | 647 | 7 | 0 |
| `html2md_streaming` | 647 | 7 | 0 |
| `html2text_rs` | 419 | 235 | 0 |
| `html_to_markdown` | 472 | 182 | 0 |
| `lxml_naive` | 256 | 397 | 1 |

### `golden`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 31 | 33 | 0 |
| `html2md` | 64 | 0 | 0 |
| `html2md_streaming` | 64 | 0 | 0 |
| `html2text_rs` | 30 | 34 | 0 |
| `html_to_markdown` | 36 | 28 | 0 |
| `lxml_naive` | 18 | 46 | 0 |

### `markdownify_tests`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 106 | 128 | 0 |
| `html2md` | 230 | 4 | 0 |
| `html2md_streaming` | 230 | 4 | 0 |
| `html2text_rs` | 86 | 148 | 0 |
| `html_to_markdown` | 127 | 107 | 0 |
| `lxml_naive` | 49 | 183 | 2 |

### `pandoc`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 1 | 7 | 0 |
| `html2md` | 6 | 2 | 0 |
| `html2md_streaming` | 6 | 2 | 0 |
| `html2text_rs` | 0 | 8 | 0 |
| `html_to_markdown` | 1 | 7 | 0 |
| `lxml_naive` | 0 | 8 | 0 |

### `turndown`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 75 | 50 | 0 |
| `html2md` | 122 | 3 | 0 |
| `html2md_streaming` | 122 | 3 | 0 |
| `html2text_rs` | 47 | 78 | 0 |
| `html_to_markdown` | 79 | 46 | 0 |
| `lxml_naive` | 30 | 94 | 1 |

### `turndown_options`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 12 | 10 | 0 |
| `html2md` | 22 | 0 | 0 |
| `html2md_streaming` | 22 | 0 | 0 |
| `html2text_rs` | 2 | 20 | 0 |
| `html_to_markdown` | 11 | 11 | 0 |
| `lxml_naive` | 1 | 21 | 0 |
