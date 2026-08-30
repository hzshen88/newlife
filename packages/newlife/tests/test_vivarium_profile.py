from __future__ import annotations

import pytest
from bigraph_schema.methods import apply, reconcile
from process_bigraph import Composite, Process, Step, allocate_core

from newlife.core.contracts import Contribution, MechanismSpec, StateClaim, StateDelta
from newlife.core.errors import CommitAuthorityError, ReadOnlyStateError
from newlife.adapters.process_bigraph.wrapper import (
    BiologicalProfile,
    GuardedProcess,
    Proposal,
    ResolvedPosition,
    allocate_profile_core,
    process_node,
    run_composite,
)


def mechanism(
    identity: str,
    *,
    claims: tuple[StateClaim, ...],
    effects: frozenset[str],
    plane: str = "biological",
) -> MechanismSpec:
    return MechanismSpec(
        identity=identity,
        version="1",
        plane=plane,
        biological_role="profile test",
        ports=("state",),
        claims=claims,
        schedule={"kind": "fixed"},
        rng_streams=(),
        allowed_effects=effects,
        invariants=(),
    )


class TestContributor(GuardedProcess):
    __test__ = False
    config_schema = {
        "mechanism_id": "string",
        "source": "string",
        "delta": "float",
    }
    lowering_table = {"Contribution": ("position", "resolved-position-envelope")}

    def inputs(self):
        return {}

    def outputs(self):
        return {"position": "biosim_resolved_position_v1"}

    def propose(self, state, interval):
        del state, interval
        effect = Contribution(
            "MechanicsResolver",
            ("position",),
            self.config["source"],
            self.config["delta"],
        )
        return Proposal(effects=(effect,))


class MutatingObserver(GuardedProcess):
    def inputs(self):
        return {"samples": {"_type": "list", "_element": "integer"}}

    def outputs(self):
        return {}

    def propose(self, state, interval):
        del interval
        state["samples"].append(99)
        return Proposal(effects=())


def test_public_profile_surface_is_available() -> None:
    core = allocate_core()
    assert issubclass(Process, object)
    assert isinstance(Step, type)
    assert Composite is not None
    assert callable(allocate_core)
    assert callable(core.register_type)
    assert callable(core.register_link)
    assert hasattr(reconcile, "dispatch")
    assert hasattr(apply, "dispatch")


def _contribution_profile(*sources: str) -> BiologicalProfile:
    profile = BiologicalProfile()
    for source in sources:
        profile.register_mechanism(
            mechanism(
                source,
                claims=(StateClaim(("position",), "contribute"),),
                effects=frozenset({"Contribution"}),
            ),
            runtime_node=f"node:{source}",
        )
    return profile


def test_two_independent_contributors_reconcile_and_apply_once() -> None:
    profile = _contribution_profile("Adhesion", "Repulsion")
    core = allocate_profile_core(("TestContributor", TestContributor))
    state = {
        "position": 1.0,
        "adhesion": process_node(
            "TestContributor",
            "Adhesion",
            inputs={},
            outputs={"position": ["position"]},
            interval=1.0,
            config={"source": "Adhesion", "delta": 2.0},
        ),
        "repulsion": process_node(
            "TestContributor",
            "Repulsion",
            inputs={},
            outputs={"position": ["position"]},
            interval=1.0,
            config={"source": "Repulsion", "delta": -0.5},
        ),
    }
    composite = Composite({"state": state}, core=core)
    run_composite(composite, 1.0, profile)
    assert composite.state["position"] == 2.5
    assert len(composite.process_paths) == 2
    assert [record["stage"] for record in profile.runtime_audit] == [
        "reconcile",
        "apply",
    ]
    assert profile.runtime_audit[-1]["sources"] == ["Adhesion", "Repulsion"]
    assert profile.assert_one_mechanism_per_node()


def test_contributor_can_be_selectively_disabled_without_collapsing_other_node() -> None:
    profile = _contribution_profile("Adhesion")
    core = allocate_profile_core(("TestContributor", TestContributor))
    state = {
        "position": 1.0,
        "adhesion": process_node(
            "TestContributor",
            "Adhesion",
            inputs={},
            outputs={"position": ["position"]},
            interval=1.0,
            config={"source": "Adhesion", "delta": 2.0},
        ),
    }
    composite = Composite({"state": state}, core=core)
    run_composite(composite, 1.0, profile)
    assert composite.state["position"] == 3.0
    assert len(composite.process_paths) == 1
    assert profile.runtime_audit[-1]["sources"] == ["Adhesion"]


def test_guarded_observer_alias_mutation_leaves_composite_state_unchanged() -> None:
    profile = BiologicalProfile()
    profile.register_mechanism(
        mechanism(
            "FitnessObserver",
            plane="evidence",
            claims=(StateClaim(("samples",), "read"),),
            effects=frozenset(),
        ),
        runtime_node="observer",
    )
    core = allocate_profile_core(("MutatingObserver", MutatingObserver))
    composite = Composite(
        {
            "state": {
                "samples": [1, 2],
                "observer": process_node(
                    "MutatingObserver",
                    "FitnessObserver",
                    inputs={"samples": ["samples"]},
                    outputs={},
                    interval=1.0,
                ),
            }
        },
        core=core,
    )
    with pytest.raises(ReadOnlyStateError):
        run_composite(composite, 1.0, profile)
    assert composite.state["samples"] == [1, 2]
    assert profile.pending_trace == []


def test_claim_violation_is_rejected_before_engine_update() -> None:
    profile = BiologicalProfile()
    profile.register_mechanism(
        mechanism(
            "Owner",
            claims=(StateClaim(("allowed",), "own"),),
            effects=frozenset({"StateDelta"}),
        )
    )
    with pytest.raises(CommitAuthorityError):
        profile.validate("Owner", [StateDelta(("forbidden",), "set", 1)])


def test_custom_resolved_type_is_a_public_schema_type() -> None:
    core = allocate_profile_core()
    assert ResolvedPosition is not None
    assert callable(core.register_type)
