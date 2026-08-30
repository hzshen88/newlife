from __future__ import annotations

import pytest

from newlife.conform.fixtures import load_fixture
from newlife.conform.contract.canonical_ruler import canonical_bytes
from newlife.adapters.process_bigraph.cases import (
    VIVARIUM_CASES,
    run_continuous_next_event,
    run_coupled_mechanics_division,
    run_execution_budget,
    run_hook_authority,
)


def test_vivarium_execution_budget_matches_frozen_answer() -> None:
    result = run_execution_budget()
    expected = load_fixture("execution_budget.json")
    assert result.trace == expected["expected_trace"]
    assert result.final_state == expected["expected_final_state"]
    assert all(result.assertions.values()), result.assertions


def test_vivarium_mechanics_division_matches_frozen_answer() -> None:
    result = run_coupled_mechanics_division()
    expected = load_fixture("coupled_mechanics_division.json")
    assert result.trace == expected["expected_trace"]
    assert result.final_state == expected["expected_final_state"]
    assert all(result.assertions.values()), result.assertions


def test_vivarium_hook_authority_matches_frozen_answer() -> None:
    result = run_hook_authority()
    expected = load_fixture("hook_authority.json")
    assert result.trace == expected["expected_trace"]
    assert result.final_state == expected["expected_final_state"]
    assert all(result.assertions.values()), result.assertions


def test_vivarium_continuous_next_event_matches_frozen_answer() -> None:
    result = run_continuous_next_event()
    expected = load_fixture("continuous_next_event.json")
    assert result.trace == expected["expected_trace"]
    assert result.final_state == expected["expected_final_state"]
    assert all(result.assertions.values()), result.assertions


@pytest.mark.parametrize("case_name", tuple(VIVARIUM_CASES))
def test_vivarium_case_replay_is_byte_identical(case_name: str) -> None:
    first = VIVARIUM_CASES[case_name]()
    second = VIVARIUM_CASES[case_name]()
    assert canonical_bytes(first.trace) == canonical_bytes(second.trace)
    assert canonical_bytes(first.final_state) == canonical_bytes(second.final_state)
