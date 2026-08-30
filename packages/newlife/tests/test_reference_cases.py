from __future__ import annotations

import pytest

from newlife.core.contracts import (
    Contribution,
    MechanismSpec,
    Resolver,
    StateClaim,
    StateDelta,
)
from newlife.core.errors import (
    CommitAuthorityError,
    DuplicateContributionError,
    IncompleteContributionSetError,
    UnknownContributionError,
)
from newlife.conform.fixtures import load_fixture
from newlife.conform.contract.canonical_ruler import canonical_bytes
from newlife.adapters.reference_kernel.cases import (
    REFERENCE_CASES,
    run_transfer_microfixture,
)
from newlife.adapters.reference_kernel.kernel import ReferenceKernel


@pytest.mark.parametrize("case_name", tuple(REFERENCE_CASES))
def test_reference_case_matches_frozen_known_answer(case_name: str) -> None:
    result = REFERENCE_CASES[case_name]()
    expected = load_fixture(f"{case_name}.json")
    assert result.trace == expected["expected_trace"]
    assert result.final_state == expected["expected_final_state"]
    assert result.negative_results
    assert all(result.assertions.values()), result.assertions


@pytest.mark.parametrize("case_name", tuple(REFERENCE_CASES))
def test_reference_case_replay_is_byte_identical(case_name: str) -> None:
    first = REFERENCE_CASES[case_name]()
    second = REFERENCE_CASES[case_name]()
    assert canonical_bytes(first.trace) == canonical_bytes(second.trace)
    assert canonical_bytes(first.final_state) == canonical_bytes(second.final_state)


def test_transfer_microfixture_matches_frozen_answer_and_conserves_total() -> None:
    result = run_transfer_microfixture()
    expected = load_fixture("effect_algebra_transfer.json")
    assert result.trace == expected["expected_trace"]
    assert result.final_state == expected["expected_final_state"]
    assert all(result.assertions.values()), result.assertions


def test_illegal_second_effect_rolls_back_complete_batch() -> None:
    kernel = ReferenceKernel({"x": 0, "y": 0})
    kernel.register_mechanism(
        MechanismSpec(
            identity="Owner",
            version="1",
            plane="biological",
            biological_role="test",
            ports=("state",),
            claims=(StateClaim(("x",), "own"),),
            schedule={},
            rng_streams=(),
            allowed_effects=frozenset({"StateDelta"}),
            invariants=(),
        )
    )
    state_before = canonical_bytes(kernel.state)
    trace_before = canonical_bytes(kernel.trace)
    with pytest.raises(CommitAuthorityError):
        kernel.apply_batch(
            "Owner",
            [StateDelta(("x",), "add", 1), StateDelta(("y",), "add", 1)],
            [{"kind": "must-not-commit"}],
        )
    assert canonical_bytes(kernel.state) == state_before
    assert canonical_bytes(kernel.trace) == trace_before


def _contribution_kernel() -> tuple[ReferenceKernel, tuple[str, ...]]:
    target = ("position",)
    kernel = ReferenceKernel({"position": "1.0"})
    for identity in ("A", "B"):
        kernel.register_mechanism(
            MechanismSpec(
                identity=identity,
                version="1",
                plane="biological",
                biological_role="contributor",
                ports=("state",),
                claims=(StateClaim(target, "contribute"),),
                schedule={},
                rng_streams=(),
                allowed_effects=frozenset({"Contribution"}),
                invariants=(),
            )
        )
    kernel.register_mechanism(
        MechanismSpec(
            identity="R",
            version="1",
            plane="biological",
            biological_role="resolver",
            ports=("state",),
            claims=(StateClaim(target, "commit"),),
            schedule={},
            rng_streams=(),
            allowed_effects=frozenset({"StateDelta"}),
            invariants=(),
        )
    )
    kernel.register_resolver(
        Resolver("R", target, frozenset({"A", "B"}), ("complete",))
    )
    return kernel, target


@pytest.mark.parametrize(
    ("items", "error"),
    [
        (
            lambda target: [
                Contribution("R", target, "A", "1.0"),
                Contribution("R", target, "A", "2.0"),
            ],
            DuplicateContributionError,
        ),
        (
            lambda target: [
                Contribution("R", target, "A", "1.0"),
                Contribution("R", target, "C", "2.0"),
            ],
            UnknownContributionError,
        ),
        (
            lambda target: [Contribution("R", target, "A", "1.0")],
            IncompleteContributionSetError,
        ),
    ],
)
def test_resolver_rejects_invalid_contribution_set_atomically(items, error) -> None:
    kernel, target = _contribution_kernel()
    before = canonical_bytes(kernel.state)
    with pytest.raises(error):
        kernel.resolve(
            "R",
            items(target),
            time="0.0",
            policy=lambda current, contributions: (current, {}),
        )
    assert canonical_bytes(kernel.state) == before
    assert kernel.trace == []
