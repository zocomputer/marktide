# marktide developer task targets.
#
# CI runs exactly two: `make lint` and `make test`. Everything else is a
# convenience subset or a utility. `make test` is the full gate (unit, component,
# conformance, property, e2e, plus the markdownify fidelity verifier); the e2e
# suite skips the >50 MiB benchmark fixtures when they are absent, so `make test`
# is runnable with nothing gitignored present. The fidelity verifier runs the
# differential corpus against real marktide and fails on any primary unallowed
# divergence — the pytest conformance layer only exercises the harness machinery.

.DEFAULT_GOAL := help
.PHONY: help lint test ruff typecheck unit conformance property e2e \
        verify-fidelity verify-canonical cov bench bench-baseline all

# `uv run` for the suite; the benchmark group provides the markdownify oracle + Rust
# adapters that the conformance/property layers and the e2e fixtures rely on.
PYTEST := uv run --group benchmark pytest

help:  ## List targets
	@awk 'BEGIN{FS=":.*## "} \
	     /^##@/{printf "\n\033[1m%s\033[0m\n", substr($$0,5); next} \
	     /^[a-zA-Z0-9_-]+:.*## /{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

##@ Primary — CI runs exactly these two
lint:  ## Ruff lint + ty type check
	uvx ruff check .
	uvx ty check src

test:  ## Full test suite: unit, component, conformance, property, e2e + fidelity gate
	$(PYTEST) tests/unit tests/component tests/conformance tests/property tests/e2e
	uv run --group benchmark python tests/conformance/verify_fidelity.py

##@ Tests — each is a subset of `make test`
unit:  ## Unit + component tests
	$(PYTEST) tests/unit tests/component

conformance:  ## Conformance / differential corpus tests
	$(PYTEST) tests/conformance

property:  ## Bounded Hypothesis property / metamorphic tests
	$(PYTEST) tests/property

e2e:  ## Black-box E2E (skips the >50 MiB fixtures when absent)
	$(PYTEST) tests/e2e

verify-fidelity:  ## Reproduce the markdownify fidelity headline (raw/effective + divergences)
	uv run --group benchmark python tests/conformance/verify_fidelity.py

verify-canonical:  ## Verify examples/canonical.html semantically across converters
	uv run --group benchmark python tests/conformance/verify_canonical.py

##@ Lint — each is a subset of `make lint`
ruff:  ## Ruff lint only
	uvx ruff check .

typecheck:  ## ty type check only
	uvx ty check src

##@ Utilities
cov:  ## Coverage report for the marktide package
	uv run --group benchmark --with pytest-cov pytest --cov=marktide --cov-report=term-missing tests/unit tests/component

bench:  ## Run the benchmark harness -> benchmarks/results/phase1.{json,md}
	uv run --group benchmark python -m benchmarks.harness.runner

bench-baseline:  ## Run the harness and write the perf-regression baseline
	uv run --group benchmark python -m benchmarks.harness.runner --output benchmarks/results/baseline.json --report benchmarks/results/baseline.md

all: lint test  ## The CI gate: lint + the full test suite
