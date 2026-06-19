"""One-command fidelity verifier for the marktide markdownify-compatibility claim.

Run from the repository root with:

    make verify-fidelity

or directly with:

    uv run --group benchmark python tests/conformance/verify_fidelity.py
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmarks.harness.adapters.base import get_adapters  # noqa: E402
from differential import CaseResult, load_cases, run_differential  # noqa: E402

PRIMARY_LAYERS = frozenset({"golden", "markdownify_tests"})
PRIMARY_LAYER_ORDER = (
    "golden",
    "markdownify_tests",
)
GUARDRAIL_LAYER_ORDER = (
    "commonmark_expected_html",
    "turndown",
    "turndown_options",
)


@dataclass(frozen=True)
class Counts:
    raw_passed: int
    effective_passed: int
    total: int
    allowed_failures: int
    unallowed_failures: tuple[str, ...]
    errors: tuple[str, ...]


def _percent(numerator: int, denominator: int) -> str:
    return f"{(numerator / denominator * 100):.1f}%" if denominator else "0.0%"


def _load_allowed_divergences() -> dict[str, str]:
    path = REPO_ROOT / "tests" / "conformance" / "allowed_divergences.toml"
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    return {
        str(entry["case_id"]): str(entry.get("reason", "documented divergence"))
        for entry in payload.get("divergence", [])
    }


def _candidate(case: CaseResult, adapter: str):
    return next(result for result in case.results if result.adapter == adapter)


def _counts(results: list[CaseResult], *, adapter: str, allowed: set[str]) -> Counts:
    raw_passed = 0
    allowed_failures = 0
    unallowed_failures: list[str] = []
    errors: list[str] = []
    for case in results:
        candidate = _candidate(case, adapter)
        if candidate.passed:
            raw_passed += 1
        elif candidate.error:
            errors.append(f"{case.id}: {candidate.error}")
        elif case.id in allowed:
            allowed_failures += 1
        else:
            unallowed_failures.append(case.id)
    return Counts(
        raw_passed=raw_passed,
        effective_passed=raw_passed + allowed_failures,
        total=len(results),
        allowed_failures=allowed_failures,
        unallowed_failures=tuple(unallowed_failures),
        errors=tuple(errors),
    )


def _fmt_counts(counts: Counts) -> str:
    return (
        f"raw {counts.raw_passed}/{counts.total} = {_percent(counts.raw_passed, counts.total)}; "
        f"effective {counts.effective_passed}/{counts.total} = {_percent(counts.effective_passed, counts.total)}"
    )


def _print_layer_summary(
    *,
    heading: str,
    underline: str,
    layers: tuple[str, ...],
    results: list[CaseResult],
    allowed_ids: set[str],
) -> None:
    print(heading)
    print(underline)
    for layer in layers:
        layer_results = [case for case in results if case.layer == layer]
        if not layer_results:
            continue
        counts = _counts(layer_results, adapter="marktide", allowed=allowed_ids)
        print(f"{layer:24} {_fmt_counts(counts)}")


def main() -> int:
    allowed = _load_allowed_divergences()
    allowed_ids = set(allowed)
    adapters = get_adapters(include_lxml_naive=False)
    cases = load_cases()
    results = run_differential(cases, adapters, max_diff_chars=300)

    primary = [case for case in results if case.layer in PRIMARY_LAYERS]
    primary_counts = _counts(primary, adapter="marktide", allowed=allowed_ids)
    primary_stream_counts = _counts(primary, adapter="marktide_streaming", allowed=allowed_ids)

    stream_mismatches = []
    for case in results:
        direct = _candidate(case, "marktide")
        streaming = _candidate(case, "marktide_streaming")
        if (
            direct.passed,
            direct.error,
            direct.normalized_output_sha256,
        ) != (
            streaming.passed,
            streaming.error,
            streaming.normalized_output_sha256,
        ):
            stream_mismatches.append(case.id)

    print("marktide PRIMARY fidelity verification")
    print("======================================")
    print("PRIMARY DROP-IN CONTRACT: golden + corrected markdownify_tests")
    print("This is the README fidelity claim. Guardrail/triangulation rows below are diagnostics.")
    print(
        "PRIMARY RESULT: "
        f"effective {primary_counts.effective_passed}/{primary_counts.total} = "
        f"{_percent(primary_counts.effective_passed, primary_counts.total)}; "
        f"raw {primary_counts.raw_passed}/{primary_counts.total} = "
        f"{_percent(primary_counts.raw_passed, primary_counts.total)}"
    )
    print(f"Primary unallowed failures: {len(primary_counts.unallowed_failures)}")
    print(
        "Primary allowed parser divergences counted as effective passes: "
        f"{primary_counts.allowed_failures}"
    )
    print(f"marktide_streaming primary check: {_fmt_counts(primary_stream_counts)}")
    print()
    _print_layer_summary(
        heading="Primary drop-in oracle breakdown (part of the 100% effective claim)",
        underline="------------------------------------------------------------------",
        layers=PRIMARY_LAYER_ORDER,
        results=results,
        allowed_ids=allowed_ids,
    )
    print()
    print("Guardrail / triangulation oracles (diagnostic only; NOT the headline claim)")
    print("-------------------------------------------------------------------------")
    print(
        "These layers compare against other tools/spec suites with different conventions. "
        "They are intentionally not expected to be 100% and do not change the primary result."
    )
    _print_layer_summary(
        heading="Guardrail layer breakdown (marktide)",
        underline="----------------------------------",
        layers=GUARDRAIL_LAYER_ORDER,
        results=results,
        allowed_ids=allowed_ids,
    )
    all_counts = _counts(results, adapter="marktide", allowed=allowed_ids)
    print(
        f"{'all_layers_diagnostic':24} {_fmt_counts(all_counts)} "
        "(diagnostic aggregate only; not the drop-in fidelity claim)"
    )
    print()
    print("Streaming parity")
    print("----------------")
    print(f"marktide vs marktide_streaming mismatches: {len(stream_mismatches)}/{len(results)}")
    print()
    print("Documented divergences that are active failures in this run")
    print("----------------------------------------------------------")
    active_primary_allowed = sorted(
        case.id
        for case in primary
        if case.id in allowed_ids and not _candidate(case, "marktide").passed
    )
    active_guardrail_allowed = sorted(
        case.id
        for case in results
        if case.layer not in PRIMARY_LAYERS
        and case.id in allowed_ids
        and not _candidate(case, "marktide").passed
    )
    if active_primary_allowed:
        print("Primary allowed divergences counted in the 100% effective claim:")
        for case_id in active_primary_allowed:
            print(f"- {case_id}: {allowed[case_id]}")
    else:
        print("Primary allowed divergences counted in the 100% effective claim: (none)")
    print()
    if active_guardrail_allowed:
        print("Guardrail-only documented divergences (diagnostic; NOT part of primary fidelity):")
        for case_id in active_guardrail_allowed:
            print(f"- {case_id}: {allowed[case_id]}")
    else:
        print("Guardrail-only documented divergences: (none)")

    failed = False
    if primary_counts.effective_passed / primary_counts.total < 0.99:
        print("ERROR: primary effective fidelity is below the 99% gate", file=sys.stderr)
        failed = True
    if primary_counts.unallowed_failures:
        print("ERROR: primary unallowed failures remain:", file=sys.stderr)
        for case_id in primary_counts.unallowed_failures:
            print(f"  - {case_id}", file=sys.stderr)
        failed = True
    if primary_counts.errors:
        print("ERROR: primary candidate errors remain:", file=sys.stderr)
        for error in primary_counts.errors:
            print(f"  - {error}", file=sys.stderr)
        failed = True
    if stream_mismatches:
        print("ERROR: streaming output differs from one-shot output:", file=sys.stderr)
        for case_id in stream_mismatches:
            print(f"  - {case_id}", file=sys.stderr)
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
