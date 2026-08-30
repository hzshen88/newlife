"""Executable probes consumed by the verdict conjunctions (never hand-entered)."""

from __future__ import annotations

import copy
from dataclasses import fields

from newlife.adapters.process_bigraph.public_api_audit import (
    audit_public_surface,
    audit_reference_dispatch,
)
from newlife.adapters.process_bigraph.wrapper import Proposal
from newlife.adapters.reference_kernel.cases import run_transfer_microfixture
from newlife.adapters.reference_kernel.kernel import ReferenceKernel
from newlife.conform.contract.canonical_ruler import (
    canonical_bytes,
    canonical_trace,
)
from newlife.conform.fixtures import load_fixture
from newlife.core.contracts import MechanismSpec, StateClaim, StateDelta, effect_tags


def api_shape_probe() -> bool:
    """R4.1: the bypass field is gone from the surface and unconstructible."""
    if "engine_update" in {f.name for f in fields(Proposal)}:
        return False
    try:
        Proposal(effects=(), engine_update={})  # type: ignore[call-arg]
    except TypeError:
        return True
    return False


def atomic_rollback_probe() -> bool:
    """Invalid Effect within a valid batch → atomic rollback (R6 housing)."""
    kernel = ReferenceKernel({"x": 0, "y": 0})
    kernel.register_mechanism(
        MechanismSpec(
            identity="AtomicOwner",
            version="1",
            plane="biological",
            biological_role="atomicity probe",
            ports=("state",),
            claims=(StateClaim(("x",), "own"),),
            schedule={},
            rng_streams=(),
            allowed_effects=frozenset({"StateDelta"}),
            invariants=(),
        )
    )
    before_state = canonical_bytes(kernel.state)
    before_trace = canonical_bytes(kernel.trace)
    try:
        kernel.apply_batch(
            "AtomicOwner",
            [StateDelta(("x",), "add", 1), StateDelta(("y",), "add", 1)],
            [{"kind": "must-not-commit"}],
        )
    except Exception as error:
        return (
            type(error).__name__ == "CommitAuthorityError"
            and canonical_bytes(kernel.state) == before_state
            and canonical_bytes(kernel.trace) == before_trace
        )
    return False


def anti_masking_probe() -> bool:
    """The four frozen maskings remain detectably unequal (R1 teeth)."""
    execution = load_fixture("execution_budget.json")["expected_trace"]
    missing_id = copy.deepcopy(execution)
    del missing_id[2]["source"]
    mechanics = load_fixture("coupled_mechanics_division.json")["expected_trace"]
    missing_contribution = [
        record
        for record in copy.deepcopy(mechanics)
        if record.get("source") != "Repulsion"
    ]
    rejections = load_fixture("hook_authority.json")["negative_cases"]
    events = load_fixture("continuous_next_event.json")["expected_trace"]
    reordered = copy.deepcopy(events)
    reordered[1], reordered[2] = reordered[2], reordered[1]
    return all(
        (
            canonical_trace(missing_id) != canonical_trace(execution),
            canonical_trace(missing_contribution) != canonical_trace(mechanics),
            canonical_bytes(rejections[:-1]) != canonical_bytes(rejections),
            canonical_trace(reordered) != canonical_trace(events),
        )
    )


def transfer_microfixture_probe() -> bool:
    fixture = load_fixture("effect_algebra_transfer.json")
    result = run_transfer_microfixture()
    return (
        all(result.assertions.values())
        and result.trace == fixture["expected_trace"]
        and result.final_state == fixture["expected_final_state"]
    )


def closed_effect_union_probe() -> bool:
    return effect_tags() == (
        "Contribution",
        "Event",
        "StateDelta",
        "StructuralRewrite",
        "Transfer",
    )


def no_fixture_specific_dispatch_probe() -> bool:
    return audit_reference_dispatch() == []


def public_surface_audit_probe() -> bool:
    return audit_public_surface() == []
