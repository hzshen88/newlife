"""Per-store-type lowering dispatch, unit-tested against synthetic IR (R5).

The adapter translation layer must be independently testable: each handler
consumes a hand-constructed LoweredOp and returns its engine-update fragment.
This is the class (ii) / class (i) diagnosability split made executable.
"""

from __future__ import annotations

import pytest

from newlife.adapters.process_bigraph.lowering import lower_update
from newlife.core.errors import SpecValidationError
from newlife.core.lowering_contract import LoweredOp


def run(store_table, effects, view=None, interval=1.0):
    return lower_update("mech", store_table, tuple(effects), view or {}, interval)


from newlife.core.contracts import (  # noqa: E402
    Contribution,
    Event,
    StateDelta,
    StructuralRewrite,
)


def test_integer_count_via_real_effect():
    update = run(
        {"StateDelta": ("count", "integer-count")},
        [StateDelta(("counts", "A"), "add", 1)],
        view={"count": 0},
    )
    assert update == {"count": 1}


def test_map_direct_via_real_effect():
    update = run(
        {"StateDelta": ("budget", "map-direct")},
        [StateDelta(("execution_budget",), "set", {"A": 2, "B": 1})],
    )
    assert update == {"budget": {"A": 2, "B": 1}}


def test_sum_float_set_computes_after_minus_observed_before():
    update = run(
        {"StateDelta": ("rate", "sum-float-set")},
        [StateDelta(("parameters", "mutation_rate"), "set", 0.2)],
        view={"rate": 0.1},
    )
    assert update["rate"] == 0.2 - 0.1  # identical arithmetic to the frozen cell


def test_string_leaf_structural_collapses_to_after():
    update = run(
        {"StructuralRewrite": ("genome", "string-leaf-structural")},
        [StructuralRewrite(("population", "p0", "genome"), "A", "B")],
    )
    assert update == {"genome": "B"}


def test_map_divide_structural_builds_the_sentinel():
    after = {"d0": {"position": 2.5, "biomass": 1.0}, "d1": {"position": 2.5, "biomass": 1.0}}
    update = run(
        {"StructuralRewrite": ("cells", "map-divide-structural")},
        [StructuralRewrite(("cells",), {"mother": {"position": 2.5, "biomass": 2.0}}, after)],
    )
    assert update == {
        "cells": {"_divide": {"mother": "mother", "daughters": after}}
    }


def test_map_divide_rejects_multi_mother_before_state():
    with pytest.raises(SpecValidationError, match="single-mother"):
        run(
            {"StructuralRewrite": ("cells", "map-divide-structural")},
            [StructuralRewrite(("cells",), {"a": 1, "b": 2}, {})],
        )


def test_budget_proposal_projection_restructures_the_payload():
    update = run(
        {"Contribution": ("proposal", "budget-proposal-projection")},
        [
            Contribution(
                "BudgetResolver",
                ("execution_budget",),
                "MeritAllocator",
                {"available_instructions": 3, "weights": {"A": 2, "B": 1}},
            )
        ],
    )
    assert update == {"proposal": {"A": 2, "B": 1, "available": 3}}


def test_resolved_position_envelope_embeds_ambient_interval():
    update = run(
        {"Contribution": ("position", "resolved-position-envelope")},
        [Contribution("MechanicsResolver", ("cells", "mother", "position"), "Adhesion", 2.0)],
        interval=1.0,
    )
    assert update == {
        "position": {
            "source": "Adhesion",
            "delta": 2.0,
            "resolver_id": "MechanicsResolver",
            "time": "1.0",
        }
    }


def test_event_op_is_state_neutral():
    update = run(
        {"Event": ("count", "noop")},
        [Event("ReactionOccurred", "mech", {"channel": "A", "count": 1})],
    )
    assert update == {}


def test_two_effects_merge_into_one_update_dict():
    update = run(
        {
            "StateDelta": ("count", "integer-count"),
            "Event": ("count", "noop"),
        },
        [
            StateDelta(("counts", "A"), "add", 1),
            Event("ReactionOccurred", "mech", {"channel": "A", "count": 1}),
        ],
    )
    assert update == {"count": 1}


def test_unbound_effect_kind_is_a_spec_error_not_a_silent_skip():
    with pytest.raises(SpecValidationError, match="no lowering binding"):
        run({"StateDelta": ("count", "integer-count")}, [Event("E", "mech", {})])


def test_unknown_store_type_is_a_spec_error():
    with pytest.raises(SpecValidationError, match="unknown store type"):
        run({"StateDelta": ("x", "mystery-store")}, [StateDelta(("x",), "add", 1)])


def test_provenance_rides_the_lowered_op_not_the_effect():
    # mechanism identity is ambient: the same effect from two wrappers lowers
    # with different provenance but identical handler input payload.
    from newlife.core.lowering_contract import lower_effect

    effect = StateDelta(("counts", "A"), "add", 1)
    first = lower_effect(effect, provenance="ReactionChannel[A]")
    second = lower_effect(effect, provenance="ReactionChannel[B]")
    assert first.provenance != second.provenance
    assert first.payload == second.payload
