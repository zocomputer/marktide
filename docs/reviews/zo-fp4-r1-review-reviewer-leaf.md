# Code Review: zo-fp4 (R1, reviewer-leaf)

- Bead: zo-fp4
- Commit range: e284552
- Reviewed commits: e284552
- Plan doc: N/A
- Reviewer: reviewer-leaf
- Review commit: e284552

## Findings

No findings.

## Verification notes

- `.github/workflows/ci.yml:4-6` registers both requested triggers: `push` and `pull_request`.
- `.github/workflows/ci.yml:14-32` is the requested minimal Ubuntu job: checkout, `astral-sh/setup-uv@v5`, `uv sync --group benchmark`, `make lint`, and `make test`.
- `.github/workflows/ci.yml:20-21` uses the `python-version` input supported by `astral-sh/setup-uv@v5`; the v5 `action.yml` defines it as the input that sets `UV_PYTHON`.
- `Makefile:21-27` confirms the two primary CI targets are `make lint` and `make test`; `Makefile:12-14` and `Makefile:26-27` confirm the full suite runs through `uv run --group benchmark pytest`.
- `pyproject.toml:11-24` confirms `uv sync --group benchmark` includes the default `dev` group (`pytest`, `hypothesis`) plus benchmark/conformance dependencies including `markdownify`.
- `Makefile:45-46` keeps `make verify-canonical` outside the CI gate, consistent with the bead note that pandoc is not required for this minimal workflow.

## Commands run

- `python - <<'PY' ...` loaded `.github/workflows/ci.yml` with PyYAML to inspect the workflow shape. PyYAML uses YAML 1.1 and reports `on` as boolean `True`, but the structure still confirms the expected triggers and steps; GitHub Actions treats `on` as the workflow trigger key.
- `make lint` — passed (`ruff check`, `ty check src`).
- `make test` — passed (`1492 passed, 1 xfailed`).

## Summary

0 findings: 0 P0, 0 P1, 0 P2, 0 P3

**Verdict**: Approved
