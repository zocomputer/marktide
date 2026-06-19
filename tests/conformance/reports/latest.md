# Conformance differential report

Full per-fixture JSON: `tests/conformance/reports/latest.json`

Case count: `1099`

## Primary markdownify-oracle fidelity

Primary layers: `golden`, `markdownify_tests`

| Adapter | Passed | Failed | Errors | Fidelity |
| --- | ---: | ---: | ---: | ---: |
| `htmd_py` | 137 | 161 | 0 | 46.0% |
| `html2text_rs` | 116 | 182 | 0 | 38.9% |
| `html_to_markdown` | 163 | 135 | 0 | 54.7% |
| `marktide` | 296 | 2 | 0 | 99.3% |
| `marktide_streaming` | 296 | 2 | 0 | 99.3% |

## Totals by adapter

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 768 | 331 | 0 |
| `html2text_rs` | 584 | 515 | 0 |
| `html_to_markdown` | 725 | 374 | 0 |
| `marktide` | 1087 | 12 | 0 |
| `marktide_streaming` | 1087 | 12 | 0 |

## Totals by layer

### `commonmark_expected_html`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 544 | 110 | 0 |
| `html2text_rs` | 419 | 235 | 0 |
| `html_to_markdown` | 472 | 182 | 0 |
| `marktide` | 647 | 7 | 0 |
| `marktide_streaming` | 647 | 7 | 0 |

### `golden`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 31 | 33 | 0 |
| `html2text_rs` | 30 | 34 | 0 |
| `html_to_markdown` | 36 | 28 | 0 |
| `marktide` | 64 | 0 | 0 |
| `marktide_streaming` | 64 | 0 | 0 |

### `markdownify_tests`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 106 | 128 | 0 |
| `html2text_rs` | 86 | 148 | 0 |
| `html_to_markdown` | 127 | 107 | 0 |
| `marktide` | 232 | 2 | 0 |
| `marktide_streaming` | 232 | 2 | 0 |

### `turndown`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 75 | 50 | 0 |
| `html2text_rs` | 47 | 78 | 0 |
| `html_to_markdown` | 79 | 46 | 0 |
| `marktide` | 122 | 3 | 0 |
| `marktide_streaming` | 122 | 3 | 0 |

### `turndown_options`

| Adapter | Passed | Failed | Errors |
| --- | ---: | ---: | ---: |
| `htmd_py` | 12 | 10 | 0 |
| `html2text_rs` | 2 | 20 | 0 |
| `html_to_markdown` | 11 | 11 | 0 |
| `marktide` | 22 | 0 | 0 |
| `marktide_streaming` | 22 | 0 | 0 |
