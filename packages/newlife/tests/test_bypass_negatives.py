"""R4 — the ten named negatives, exactly as frozen in the v0.1a preregistration.

Every rejection must leave state bytes unchanged. Negatives 3–8 are the six
inherited permission types (asserted here against both targets' case results,
where the frozen cases already drive them); 1, 2, 9, 10 are the new
bypass-closure negatives with direct probes. R4.9 lives in
test_lowering_controls.py; R4.10's vivarium-side probe is here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from newlife.adapters.process_bigraph.wrapper import Proposal
from newlife.adapters.reference_kernel.cases import REFERENCE_CASES
from newlife.adapters.process_bigraph.cases import VIVARIUM_CASES
from newlife.conform.contract.canonical_ruler import canonical_bytes
from newlife.conform.fixtures import load_fixture

NEWLIFE_SRC = Path(__file__).resolve().parents[1] / "src" / "newlife"
REPO_ROOT = Path(__file__).resolve().parents[3]

INHERITED_NEGATIVES = {  # R4 negatives 3–8, per target
    "execution_budget": {"scheduler_state_write": "PlaneAuthorityError"},
    "coupled_mechanics_division": {
        "adhesion_direct_commit": "CommitAuthorityError",
        "repulsion_direct_commit": "CommitAuthorityError",
        "competing_division": "StructuralOwnershipConflictError",
    },
    "hook_authority": {
        "observer_nested_alias_mutation": "ReadOnlyStateError",
        "intervention_genome_write": "InterventionScopeError",
        "sixth_effect_registration": "UnknownEffectKindError",
    },
}


def _negatives(case_result):
    return {item["name"]: item for item in case_result.negative_results}


@pytest.mark.parametrize("target,cases", [("reference", REFERENCE_CASES), ("vivarium", VIVARIUM_CASES)])
@pytest.mark.parametrize("case_name", tuple(INHERITED_NEGATIVES))
def test_inherited_permission_negatives_fire_with_exact_typed_errors(target, cases, case_name):
    result = cases[case_name]()
    observed = _negatives(result)
    for name, expected_error in INHERITED_NEGATIVES[case_name].items():
        assert observed[name]["error"] == expected_error
        assert observed[name]["state_unchanged"] is True
        assert observed[name]["trace_unchanged"] is True


def test_negative_1_api_shape_proposal_has_no_engine_update():
    # field gone AND unconstructible: construction with it is a TypeError
    assert "engine_update" not in Proposal.__dataclass_fields__
    with pytest.raises(TypeError):
        Proposal(effects=(), engine_update={})  # type: ignore[call-arg]


def test_negative_2_import_lint_confines_vendor_and_bans_engine_update():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_imports.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout
    # no adapter (or any src) file references the removed bypass field
    offenders = [
        str(path.relative_to(NEWLIFE_SRC))
        for path in NEWLIFE_SRC.rglob("*.py")
        if "engine_update" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_negative_9_tampered_lowering_control_is_detected():
    # covered in depth in test_lowering_controls.py; assert here that the
    # named control exists and bites, so the set of ten is checkable in one place
    import newlife.adapters.reference_kernel.kernel as kernel_module

    original = kernel_module.apply_op

    def tampered(state, op):
        if op.op == "add":
            op = type(op)(op.path, "set", op.payload, op.provenance)
        return original(state, op)

    kernel_module.apply_op = tampered
    try:
        result = REFERENCE_CASES["execution_budget"](include_negatives=False)
    finally:
        kernel_module.apply_op = original
    expected = load_fixture("execution_budget.json")
    assert canonical_bytes(result.final_state) != canonical_bytes(expected["expected_final_state"])


def test_negative_10_vivarium_payload_side_channel_does_not_alter_committed_state():
    # A process proposes a StateDelta carrying a mutable list; the container
    # is mutated after update() has committed — the composite state must hold
    # the value as of the write boundary, not the mutated alias.
    import copy

    from newlife.adapters.process_bigraph.wrapper import (
        BiologicalProfile,
        GuardedProcess,
        allocate_profile_core,
        process_node,
        run_composite,
    )
    from newlife.core.contracts import MechanismSpec, StateClaim, StateDelta
    from process_bigraph import Composite

    payload = [1, 2]

    class ListOwner(GuardedProcess):
        lowering_table = {"StateDelta": ("items", "list-direct")}

        def inputs(self):
            return {}

        def outputs(self):
            return {"items": {"_type": "list", "_element": "integer"}}

        def propose(self, state, interval):
            del state, interval
            return Proposal(effects=(StateDelta(("box", "items"), "set", payload),))

    profile = BiologicalProfile()
    profile.register_mechanism(
        MechanismSpec(
            identity="ListOwner",
            version="1",
            plane="biological",
            biological_role="side-channel probe",
            ports=("state",),
            claims=(StateClaim(("box", "items"), "own"),),
            schedule={},
            rng_streams=(),
            allowed_effects=frozenset({"StateDelta"}),
            invariants=(),
        ),
        "list-owner",
    )
    core = allocate_profile_core(("ListOwner", ListOwner))
    state = {
        "box": {"items": [0]},
        "owner_node": process_node(
            "ListOwner",
            "ListOwner",
            inputs={},
            outputs={"items": ["box", "items"]},
            interval=1.0,
        ),
    }
    composite = Composite({"state": state}, core=core)
    run_composite(composite, 1.0, profile)
    payload.append(3)  # mutation after the commit boundary
    assert copy.deepcopy(composite.state["box"]["items"]) != [1, 2, 3]
