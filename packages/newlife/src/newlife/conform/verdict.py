"""v0.1a verdict runner: the frozen conjunctions, computed mechanically.

Prereg (2026-08-30): the ``single_write_path`` verdict is
``compatible_for_frozen_slices_v1_lowered`` only if all 8 cells, all
applicable negatives, replay checks, digest checks, import-lint, and the
tamper control pass. Missing cell or assertion → nonzero exit. Cells pass /
negatives fail ⇒ verdict withheld as an evidence-engineering failure. A
failing cell is classified before any verdict (R5): class (i) payload gap →
H0; class (ii) mistranslation → implementation clarification; neither →
anomaly protocol.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import signal
import subprocess
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterator

from newlife.adapters.process_bigraph.cases import VIVARIUM_CASES
from newlife.adapters.reference_kernel.cases import REFERENCE_CASES
from newlife.conform.contract.canonical_ruler import canonical_bytes
from newlife.conform.fixtures import FROZEN_FIXTURE_SHA256, fixture_hashes, load_fixture
from newlife.conform.manifest import build_manifest, source_tree_digest
from newlife.conform.probes import (
    anti_masking_probe,
    api_shape_probe,
    atomic_rollback_probe,
    closed_effect_union_probe,
    declaration_side_channel_probe,
    no_fixture_specific_dispatch_probe,
    orchestration_tamper_probe,
    public_surface_audit_probe,
    staging_validation_negatives_probe,
    transfer_microfixture_probe,
)

CELL_TIMEOUT_SECONDS = 120
SUITE_TIMEOUT_SECONDS = 20 * 60
VERDICT_PASS = "compatible_for_frozen_slices_v1_lowered"
VERDICT_REJECT = "reject"
VERDICT_WITHHELD = "verdict_withheld_evidence_engineering_failure"
STAGING_VERDICT_PASS = "staging_declarable_for_frozen_slices"

# Frozen formal prediction P4 (preregistration 2026-08-31): the expected
# composite sequences per slice; the compiler's record must equal these.
FROZEN_P4 = {
    "execution_budget": {
        "carried_roots": ["execution_budget", "organisms"],
        "stages": [
            {"label": "allocate", "duration": 0.0,
             "mechanisms": ["BudgetResolver", "MeritAllocator"],
             "state_roots": ["budget_proposal", "execution_budget", "organisms"],
             "internal_roots": ["budget_proposal"]},
            {"label": "instruct-a", "duration": 1.0,
             "mechanisms": ["InstructionMechanism[A]"],
             "state_roots": ["execution_budget", "organisms"],
             "internal_roots": []},
            {"label": "instruct-b", "duration": 1.0,
             "mechanisms": ["InstructionMechanism[B]"],
             "state_roots": ["execution_budget", "organisms"],
             "internal_roots": []},
        ],
    },
    "coupled_mechanics_division": {
        "carried_roots": ["cells"],
        "stages": [
            {"label": "mechanics", "duration": 1.0,
             "mechanisms": ["Adhesion", "Repulsion"],
             "state_roots": ["cells"], "internal_roots": []},
            {"label": "division", "duration": 1.0,
             "mechanisms": ["DivisionMechanism"],
             "state_roots": ["cells"], "internal_roots": []},
        ],
    },
    "hook_authority": {
        "carried_roots": ["parameters", "population"],
        "stages": [
            {"label": "intervene", "duration": 1.0,
             "mechanisms": ["MutationRateIntervention"],
             "state_roots": ["parameters", "population"], "internal_roots": []},
            {"label": "mutate", "duration": 1.0,
             "mechanisms": ["MutationMechanism"],
             "state_roots": ["parameters", "population"], "internal_roots": []},
            {"label": "observe", "duration": 1.0,
             "mechanisms": ["FitnessObserver"],
             "state_roots": ["parameters", "population"], "internal_roots": []},
        ],
    },
    "continuous_next_event": {
        "carried_roots": ["counts"],
        "stages": [
            {"label": "react", "duration": 1.0,
             "mechanisms": ["ReactionChannel[A]", "ReactionChannel[B]"],
             "state_roots": ["counts"], "internal_roots": []},
        ],
    },
}

IMPLEMENTATION_LOG_V01B: list[dict[str, Any]] = [
    {
        "classification": "implementation clarification",
        "issue": "R2 lists the Step/Process mixed-stage check under profile "
        "validation, but node types are adapter knowledge invisible to the "
        "profile",
        "correction": "enforced at compiler entry (staging.py) before any "
        "composite runs — the frozen R2 error semantics (StageValidationError) "
        "are preserved",
        "criterion_changed": False,
    },
    {
        "classification": "implementation clarification",
        "issue": "mechanism identities contain characters like '[' that the "
        "engine parses in state path segments, so composite node state keys "
        "cannot be mechanism ids",
        "correction": "composite node state keys are positional (node_0, …); "
        "the mechanism identity travels in the node config (mechanism_id)",
        "criterion_changed": False,
    },
    {
        "classification": "implementation clarification",
        "issue": "P1's schema-zero initialization needs the producer's "
        "declared output schema, which lives on the process class where the "
        "compiler cannot read it without instantiating the engine",
        "correction": "the producer's declared output schema is declared at "
        "the wiring layer (output_schemas) — the same declaration, readable "
        "where the derivation runs",
        "criterion_changed": False,
    },
    {
        "classification": "implementation clarification",
        "issue": "compile-time plans carry the declared initial state, so "
        "later stages would start from initial values instead of the prior "
        "stage's committed state",
        "correction": "run_orchestration threads carried-root values from "
        "the previous stage's committed state (the basis term); the P1 root "
        "SET remains compile-time and programmatically asserted",
        "criterion_changed": False,
    },
    {
        "classification": "evidence-engineering correction",
        "issue": "this v0.1b log was shadowed by a duplicate v0.1a "
        "IMPLEMENTATION_LOG definition later in this module (Python name "
        "rebinding), so the first evidence bundle, its manifest, and the "
        "no_criterion_deviation conjunction consumed the PREVIOUS "
        "experiment's log — caught in acceptance review",
        "correction": "logs split into IMPLEMENTATION_LOG_V01A/_V01B; this "
        "bundle re-issued with the true v0.1b log (5 entries); "
        "no_criterion_deviation now checks the union of both experiments' "
        "logs; ruff F811 added to the CI gate; every verdict bundle write "
        "is read back and verified",
        "criterion_changed": False,
    },
]
IMPLEMENTATION_LOG_V01A: list[dict[str, Any]] = [
    # The v0.1a experiment's log, archived with its bundle
    # (results/v0.1a, exloop artifacts/lowering-results). Kept here so the
    # no_criterion_deviation conjunction covers both experiments' logs.
    {
        "classification": "implementation clarification",
        "issue": "deep-copying Effects in stage() crashed on Event payloads "
        "(frozen immutable mapping views are not deep-copyable)",
        "correction": "pass validated Effects through unchanged; alias "
        "isolation is provided at the write boundary (update's deep-copied "
        "return), which is where the side-channel negative probes it",
        "criterion_changed": False,
    },
    {
        "classification": "implementation clarification",
        "issue": "the tampered-lowering control's set→add flip is "
        "byte-invisible on fixture A's zero-initialized budget store, and no "
        "lowering tamper can alter mechanism-handwritten trace records",
        "correction": "control implemented as add→set on fixture A and "
        "set→add on fixture C (both detected via the final-state half of the "
        "frozen byte comparison); the trace half's teeth are proven by the "
        "anti-masking probes, and the transfer microfixture adds a "
        "conservation-skimming probe",
        "criterion_changed": False,
    },
    {
        "classification": "implementation clarification",
        "issue": "the vivarium-side payload side-channel negative needed a "
        "list-store lowering binding",
        "correction": "added the list-direct store type (set = whole-list "
        "overwrite) to the dispatch table",
        "criterion_changed": False,
    },
]


class FormalTimeoutError(TimeoutError):
    pass


@contextmanager
def timeout(seconds: int) -> Iterator[None]:
    def handler(_signum, _frame):
        raise FormalTimeoutError(f"formal invocation exceeded {seconds} seconds")

    previous = signal.signal(signal.SIGALRM, handler)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    started = time.monotonic()
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        if previous_timer[0] > 0:
            elapsed = time.monotonic() - started
            remaining = max(previous_timer[0] - elapsed, 0.000001)
            signal.setitimer(signal.ITIMER_REAL, remaining, previous_timer[1])


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Read-back verification: a claimed bundle write must be re-read and
    # compared — the acceptance-review shadowed-log defect is exactly the
    # failure mode this closes.
    reread = json.loads(path.read_text(encoding="utf-8"))
    if reread != value:
        raise RuntimeError(f"bundle write verification failed: {path}")


def negative_cases_exact(case_result, fixture: dict[str, Any]) -> bool:
    actual = {item["name"]: item for item in case_result.negative_results}
    expected = {item["name"]: item for item in fixture.get("negative_cases", [])}
    if set(actual) != set(expected):
        return False
    for name, frozen in expected.items():
        observed = actual[name]
        for key, value in frozen.items():
            if observed.get(key) != value:
                return False
    return True


def required_assertions_exact(case_result, fixture: dict[str, Any]) -> bool:
    return all(
        case_result.assertions.get(name) is True
        for name in fixture["required_assertions"]
    )


def compute_verdict(
    cell_checks: dict[str, bool],
    engineering_checks: dict[str, bool],
    pass_verdict: str = VERDICT_PASS,
) -> str:
    """Frozen decision rules: cells ∧ engineering ⇒ pass; cells pass but
    engineering fails ⇒ withheld (a toothless ruler voids the positives);
    any cell fails ⇒ reject (with classification recorded separately)."""
    cells_pass = all(cell_checks.values())
    if cells_pass and all(engineering_checks.values()):
        return pass_verdict
    if cells_pass:
        return VERDICT_WITHHELD
    return VERDICT_REJECT


def pytest_output_passed(text: str) -> bool:
    # silent-degradation: ok —— 这是谓词函数，「最后一行不是 N passed」正是它要报告的否定结果
    success = re.compile(r"^\d+ passed in \d+(?:\.\d+)?s$")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return bool(lines) and success.fullmatch(lines[-1]) is not None


def run_cells(output: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, bool]], int, int]:
    primary: dict[str, dict[str, Any]] = {"reference": {}, "vivarium": {}}
    cell_passes: dict[str, dict[str, bool]] = {"reference": {}, "vivarium": {}}
    positive_count = 0
    negative_count = 0
    for target, cases in (("reference", REFERENCE_CASES), ("vivarium", VIVARIUM_CASES)):
        for name, case in cases.items():
            with timeout(CELL_TIMEOUT_SECONDS):
                first = case(include_negatives=True)
            with timeout(CELL_TIMEOUT_SECONDS):
                replay = case(include_negatives=False)
            positive_count += 2
            negative_count += len(first.negative_results)
            replay_equal = (
                canonical_bytes(first.trace) == canonical_bytes(replay.trace)
                and canonical_bytes(first.final_state) == canonical_bytes(replay.final_state)
            )
            first.assertions["byte_identical_replay"] = replay_equal
            fixture = load_fixture(f"{name}.json")
            negative_exact = negative_cases_exact(first, fixture)
            required_exact = required_assertions_exact(first, fixture)
            passed = all(first.assertions.values()) and negative_exact and required_exact
            record = asdict(first)
            record["replay"] = {
                "byte_identical": replay_equal,
                "trace_sha256": hashlib.sha256(canonical_bytes(replay.trace)).hexdigest(),
                "state_sha256": hashlib.sha256(canonical_bytes(replay.final_state)).hexdigest(),
            }
            record["negative_cases_exact"] = negative_exact
            record["required_assertions_exact"] = required_exact
            record["passed"] = passed
            primary[target][name] = record
            cell_passes[target][name] = passed
            write_json(output / target / f"{name}.json", record)
    return primary, cell_passes, positive_count, negative_count


def execute(output: Path, pytest_text: str) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    manifest["analysis_code_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()

    primary, cell_passes, positive_count, negative_count = run_cells(output)

    roots = {name: Path(path) for name, path in manifest["installed_source_roots"].items()}
    after_hashes = {name: source_tree_digest(path) for name, path in roots.items()}
    manifest["installed_source_sha256_after"] = after_hashes
    manifest["formal_counts"] = {
        "target_slice_cells": 8,
        "staged_orchestration_units": 4,
        "positive_executions": positive_count,
        "negative_executions_cell_level": negative_count,
        "contract_microfixtures": 1,
        "named_negative_types_v0_1a": 10,
        "named_negative_types_v0_1b": 8,
    }
    manifest["implementation_log"] = IMPLEMENTATION_LOG_V01B

    frozen_data_exact = fixture_hashes() == FROZEN_FIXTURE_SHA256
    import_lint = subprocess.run(
        ["python3", "scripts/check_imports.py"], capture_output=True, text=True
    )
    counts_exact = positive_count == 16 and negative_count == 18

    cases_source = (
        Path(__file__).resolve().parents[1]
        / "adapters" / "process_bigraph" / "cases.py"
    ).read_text(encoding="utf-8")
    staging_cell_checks = {
        "all_vivarium_cells": all(cell_passes["vivarium"].values()),
        "p4_orchestration_predictions": all(
            primary["vivarium"][name]["metadata"].get("orchestration") == FROZEN_P4[name]
            for name in VIVARIUM_CASES
        ),
    }
    staging_engineering_checks = {
        "staging_validation_negatives": staging_validation_negatives_probe(),
        "declaration_side_channel": declaration_side_channel_probe(),
        "orchestration_tamper_control": orchestration_tamper_probe(),
        "reference_stage_order_predicate": all(
            primary["reference"][name]["assertions"]["declared_stage_order_valid"]
            for name in REFERENCE_CASES
        ),
        "no_manual_composite_in_cases": "Composite(" not in cases_source,
        "installed_sources_unchanged": after_hashes
        == manifest["installed_source_sha256_before"],
        "frozen_data_unchanged": frozen_data_exact,
        "import_lint_clean": import_lint.returncode == 0,
        "pytest_suite": pytest_output_passed(pytest_text),
        "no_criterion_deviation": not any(
            entry["criterion_changed"]
            for entry in IMPLEMENTATION_LOG_V01A + IMPLEMENTATION_LOG_V01B
        ),
    }
    staging_verdict = compute_verdict(
        staging_cell_checks, staging_engineering_checks, pass_verdict=STAGING_VERDICT_PASS
    )
    cell_checks = {
        "all_reference_cells": all(cell_passes["reference"].values()),
        "all_vivarium_cells": all(cell_passes["vivarium"].values()),
        "cross_target_exact": all(
            canonical_bytes(primary["reference"][name]["trace"])
            == canonical_bytes(primary["vivarium"][name]["trace"])
            and canonical_bytes(primary["reference"][name]["final_state"])
            == canonical_bytes(primary["vivarium"][name]["final_state"])
            for name in REFERENCE_CASES
        ),
        "transfer_microfixture": transfer_microfixture_probe(),
    }
    engineering_checks = {
        "closed_effect_union": closed_effect_union_probe(),
        "atomic_batch_rollback": atomic_rollback_probe(),
        "api_shape_bypass_removed": api_shape_probe(),
        "no_fixture_specific_dispatch": no_fixture_specific_dispatch_probe(),
        "normalizer_anti_masking": anti_masking_probe(),
        "public_surface_audit": public_surface_audit_probe(),
        "installed_sources_unchanged": after_hashes
        == manifest["installed_source_sha256_before"],
        "frozen_data_unchanged": frozen_data_exact,
        "import_lint_clean": import_lint.returncode == 0,
        "pytest_suite": pytest_output_passed(pytest_text),
        "no_criterion_deviation": not any(
            entry["criterion_changed"]
            for entry in IMPLEMENTATION_LOG_V01A + IMPLEMENTATION_LOG_V01B
        ),
    }
    verdict = compute_verdict(cell_checks, engineering_checks)
    summary = {
        "schema_version": 1,
        "scope": "v0.1b-staging-declarability-frozen-slices",
        "staging_checks": staging_cell_checks,
        "staging_engineering_checks": staging_engineering_checks,
        "staging_verdict": staging_verdict,
        "cell_checks": cell_checks,
        "engineering_checks": engineering_checks,
        "cell_passes": cell_passes,
        "single_write_path_verdict": verdict,
        "limitations": [
            "completeness for four frozen slices on contract v1 only",
            "no claim of universal lowering, biological validity, or performance",
            "trace-format switching to the proofroot spec deferred to v0.2",
        ],
    }
    write_json(output / "manifest.json", manifest)
    write_json(output / "summary.json", summary)
    write_json(output / "implementation-log.json", IMPLEMENTATION_LOG_V01B)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pytest-output", type=Path, required=True)
    args = parser.parse_args()
    pytest_text = args.pytest_output.read_text(encoding="utf-8")
    with timeout(SUITE_TIMEOUT_SECONDS):
        summary = execute(args.output, pytest_text)
    print(json.dumps(summary, indent=2, sort_keys=True))
    passed = (
        summary["single_write_path_verdict"] == VERDICT_PASS
        and summary["staging_verdict"] == STAGING_VERDICT_PASS
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
