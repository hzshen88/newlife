"""R2 lowering-contract unit tests: mapping tables + provenance binding.

Every Effect kind maps to exactly one LoweredOp with the exact R2 op tag and
payload shape; error cases (distinct Transfer paths, non-empty identities)
are part of the mapping; provenance is ambient — same Effects under different
mechanism identities yield different provenance with identical payloads.
"""

from __future__ import annotations

import pytest

from newlife.core.contracts import (
    Contribution,
    Event,
    StateDelta,
    StructuralRewrite,
    Transfer,
)
from newlife.core.errors import SpecValidationError
from newlife.core.lowering_contract import (
    LOWERED_OPS,
    OP_ADD,
    OP_CONTRIBUTION_RESOLVE,
    OP_EVENT,
    OP_SET,
    OP_STRUCTURAL,
    OP_TRANSFER_PAIR,
    LoweredOp,
    lower_effect,
)


def test_op_enumeration_is_exactly_r2():
    assert LOWERED_OPS == frozenset(
        {"set", "add", "transfer_pair", "structural", "contribution_resolve", "event"}
    )


def test_state_delta_set_maps_to_set_op():
    op = lower_effect(StateDelta(("a", "b"), "set", 7), provenance="mech")
    assert op == LoweredOp(("a", "b"), OP_SET, 7, "mech")


def test_state_delta_add_maps_to_add_op():
    op = lower_effect(StateDelta(("counts", "A"), "add", 1), provenance="mech")
    assert op == LoweredOp(("counts", "A"), OP_ADD, 1, "mech")


def test_transfer_maps_to_transfer_pair_carrying_both_paths():
    op = lower_effect(
        Transfer(("medium", "nutrient"), ("cell", "energy"), "0.25"), provenance="transport"
    )
    assert op.op == OP_TRANSFER_PAIR
    assert op.path == ("medium", "nutrient")
    assert op.payload == {
        "source_path": ("medium", "nutrient"),
        "destination_path": ("cell", "energy"),
        "amount": "0.25",
    }


def test_structural_rewrite_maps_before_after_pair():
    op = lower_effect(StructuralRewrite(("cells",), {"m": 1}, {"d0": 1, "d1": 1}), provenance="div")
    assert op == LoweredOp(
        ("cells",), OP_STRUCTURAL, {"before": {"m": 1}, "after": {"d0": 1, "d1": 1}}, "div"
    )


def test_contribution_stops_at_contribution_resolve():
    op = lower_effect(
        Contribution("res", ("p",), "src", {"delta": 1.5}), provenance="src"
    )
    assert op == LoweredOp(
        ("p",),
        OP_CONTRIBUTION_RESOLVE,
        {"resolver_id": "res", "source_id": "src", "value": {"delta": 1.5}},
        "src",
    )


def test_event_maps_to_event_op_with_no_path():
    op = lower_effect(Event("Observed", "observer", {"k": "v"}), provenance="observer")
    assert op == LoweredOp(
        None, OP_EVENT, {"event_type": "Observed", "payload": {"k": "v"}}, "observer"
    )


def test_unknown_effect_kind_is_a_contract_violation_not_a_lowering_choice():
    class Mystery:
        kind = "Mystery"

    with pytest.raises(SpecValidationError, match="unknown Effect kind"):
        lower_effect(Mystery(), provenance="mech")  # type: ignore[arg-type]


def test_empty_provenance_is_rejected():
    with pytest.raises(SpecValidationError, match="provenance"):
        lower_effect(StateDelta(("a",), "set", 1), provenance="")


def test_provenance_is_ambient_not_an_effect_field():
    # Same effects, different mechanism identities: different provenance,
    # identical (op, path, payload).
    effect = StateDelta(("budget",), "set", {"A": 2})
    first = lower_effect(effect, provenance="mechanism_one")
    second = lower_effect(effect, provenance="mechanism_two")
    assert first.provenance == "mechanism_one"
    assert second.provenance == "mechanism_two"
    assert (first.op, first.path, first.payload) == (second.op, second.path, second.payload)


def test_one_effect_is_exactly_one_lowered_op():
    effect = StateDelta(("x",), "add", 1)
    ops = [lower_effect(effect, provenance="m")]
    assert len(ops) == 1


def test_transfer_rejects_identical_paths():
    with pytest.raises(Exception, match="distinct"):
        Transfer(("a",), ("a",), 1)
