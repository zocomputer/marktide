# html2md developer task targets.
#
# Commands mirror the conventions used across the project: `uv run` for the test
# suite (dev deps come from the [dependency-groups].dev group), and `uvx` for
# tools that are not in the dependency group (ruff, ty, pytest-cov).

.DEFAULT_GOAL := help
.PHONY: help test conformance property e2e e2e-full cov lint typecheck bench bench-baseline all

PYTEST := uv run pytest

help:  ## List available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

test:  ## Fast unit + component tests (PR gate)
	$(PYTEST) tests/unit tests/component

conformance:  ## Conformance / differential corpus tests
	$(PYTEST) tests/conformance

property:  ## Bounded Hypothesis property / metamorphic tests
	$(PYTEST) tests/property

e2e:  ## Black-box E2E (inline + huge_tree + small/medium fixtures)
	$(PYTEST) tests/e2e

e2e-full:  ## Black-box E2E incl. large/xlarge fixtures (nightly / on-demand)
	$(PYTEST) tests/e2e --run-nightly

cov:  ## Unit + component coverage report for the html2md package
	uv run --with pytest-cov pytest --cov=html2md --cov-report=term-missing tests/unit tests/component

lint:  ## Ruff lint
	uvx ruff check .

typecheck:  ## Static type check (ty) of the package
	uvx ty check src

bench:  ## Run the phase-1 benchmark harness -> benchmarks/results/phase1.{json,md}
	uv run python -m benchmarks.harness.runner

bench-baseline:  ## Run the harness and write the perf-regression baseline
	uv run python -m benchmarks.harness.runner --output benchmarks/results/baseline.json --report benchmarks/results/baseline.md

all: lint typecheck test conformance property e2e  ## Lint + typecheck + the full PR test suite
