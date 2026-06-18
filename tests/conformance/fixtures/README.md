# Vendored conformance fixtures

These files are committed intentionally so `make test` runs the same conformance corpus in a clean GitHub Actions checkout as it does on a developer machine.

Source provenance is tracked in `tests/conformance/sources.toml`. In particular, the markdownify corpus under `tests/conformance/fixtures/markdownify/` is copied from `matthewwithanm/python-markdownify` commit `add391a6235cbc66af30ec0202cb00cb0ff0eb4c`. That commit is the fixture source for the upstream test files; the live markdownify oracle dependency used to compute expected output is controlled separately by `pyproject.toml` / `uv.lock`.

Regenerate these fixtures with:

```bash
python scripts/regenerate_conformance_corpus.py
```
