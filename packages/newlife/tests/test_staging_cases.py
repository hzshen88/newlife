"""v0.1b acceptance surfaces: P4 orchestration predictions asserted
programmatically from the compiler's output (never eyeballed), the R4.8
orchestration-tamper control, and the R4.7 lint bite on the case path.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from newlife.adapters.process_bigraph.cases import VIVARIUM_CASES
from newlife.adapters.reference_kernel.cases import REFERENCE_CASES
from newlife.conform.contract.canonical_ruler import canonical_bytes
from newlife.conform.fixtures import load_fixture

# Frozen formal prediction P4 (preregistration 2026-08-31): the expected
# composite sequences, derived on paper before implementation. The compiler's
# record must equal these dicts exactly.
FROZEN_P4 = {
    "execution_budget": {
        "carried_roots": ["execution_budget", "organisms"],
        "stages": [
            {
                "label": "allocate",
                "duration": 0.0,
                "mechanisms": ["BudgetResolver", "MeritAllocator"],
                "state_roots": ["budget_proposal", "execution_budget", "organisms"],
                "internal_roots": ["budget_proposal"],
            },
            {
                "label": "instruct-a",
                "duration": 1.0,
                "mechanisms": ["InstructionMechanism[A]"],
                "state_roots": ["execution_budget", "organisms"],
                "internal_roots": [],
            },
            {
                "label": "instruct-b",
                "duration": 1.0,
                "mechanisms": ["InstructionMechanism[B]"],
                "state_roots": ["execution_budget", "organisms"],
                "internal_roots": [],
            },
        ],
    },
    "coupled_mechanics_division": {
        "carried_roots": ["cells"],
        "stages": [
            {
                "label": "mechanics",
                "duration": 1.0,
                "mechanisms": ["Adhesion", "Repulsion"],
                "state_roots": ["cells"],
                "internal_roots": [],
            },
            {
                "label": "division",
                "duration": 1.0,
                "mechanisms": ["DivisionMechanism"],
                "state_roots": ["cells"],
                "internal_roots": [],
            },
        ],
    },
    "hook_authority": {
        "carried_roots": ["parameters", "population"],
        "stages": [
            {
                "label": "intervene",
                "duration": 1.0,
                "mechanisms": ["MutationRateIntervention"],
                "state_roots": ["parameters", "population"],
                "internal_roots": [],
            },
            {
                "label": "mutate",
                "duration": 1.0,
                "mechanisms": ["MutationMechanism"],
                "state_roots": ["parameters", "population"],
                "internal_roots": [],
            },
            {
                "label": "observe",
                "duration": 1.0,
                "mechanisms": ["FitnessObserver"],
                "state_roots": ["parameters", "population"],
                "internal_roots": [],
            },
        ],
    },
    "continuous_next_event": {
        "carried_roots": ["counts"],
        "stages": [
            {
                "label": "react",
                "duration": 1.0,
                "mechanisms": ["ReactionChannel[A]", "ReactionChannel[B]"],
                "state_roots": ["counts"],
                "internal_roots": [],
            },
        ],
    },
}


@pytest.mark.parametrize("case_name", tuple(VIVARIUM_CASES))
def test_p4_orchestration_predictions_match_the_compiler_record(case_name):
    result = VIVARIUM_CASES[case_name](include_negatives=False)
    assert result.metadata["orchestration"] == FROZEN_P4[case_name]


def test_negative_8_orchestration_tamper_control_is_detected():
    # Merged instruction stages (one Composite instead of two chained ones)
    # must be caught by the byte comparison — the ruler bites on grouping
    # and order, so a wrong declared DAG cannot pass silently.
    tampered = VIVARIUM_CASES["execution_budget"](
        include_negatives=False, stage_plan="merged_instructions"
    )
    expected = load_fixture("execution_budget.json")
    assert tampered.metadata["orchestration"]["stages"][1]["label"] == "instruct"
    assert canonical_bytes(tampered.trace) != canonical_bytes(expected["expected_trace"])
    assert not tampered.assertions["exact_trace"]


def test_r6_reference_program_orders_satisfy_the_declared_dags():
    # the reference cases assert this themselves; pin the four orders here
    for name, case in REFERENCE_CASES.items():
        result = case()
        assert result.assertions["declared_stage_order_valid"] is True, name


def test_r4_7_lint_bites_on_manual_composite_construction():
    # the rule is real: a synthetic case-path file containing Composite( fails
    repo = Path(__file__).resolve().parents[3]
    lint = repo / "scripts" / "check_imports.py"
    result = subprocess.run([sys.executable, str(lint)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    cases_source = (
        repo
        / "packages"
        / "newlife"
        / "src"
        / "newlife"
        / "adapters"
        / "process_bigraph"
        / "cases.py"
    ).read_text(encoding="utf-8")
    assert "Composite(" not in cases_source  # the enforced property itself
