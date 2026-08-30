"""Frozen slices implemented as independent Process-Bigraph compositions."""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any, Callable

from process_bigraph import Composite

from newlife.core.contracts import (
    Contribution,
    Event,
    MechanismSpec,
    Resolver,
    StateClaim,
    StateDelta,
    StructuralRewrite,
)
from newlife.core.errors import InvalidIntervalError
from newlife.conform.fixtures import load_fixture
from newlife.conform.contract.canonical_ruler import canonical_bytes, canonical_state, canonical_trace
from newlife.adapters.reference_kernel.kernel import CaseResult
from newlife.adapters.process_bigraph.wrapper import (
    BiologicalProfile,
    GuardedProcess,
    GuardedStep,
    Proposal,
    active_profile,
    allocate_profile_core,
    process_node,
    run_composite,
    step_node,
)


def _spec(
    identity: str,
    *,
    plane: str,
    role: str,
    claims: tuple[StateClaim, ...] = (),
    effects: frozenset[str] = frozenset(),
    rng_streams: tuple[str, ...] = (),
) -> MechanismSpec:
    return MechanismSpec(
        identity=identity,
        version="1.0.0",
        plane=plane,
        biological_role=role,
        ports=("state",),
        claims=claims,
        schedule={"kind": "runtime-managed"},
        rng_streams=rng_streams,
        allowed_effects=effects,
        invariants=("frozen-fixture",),
    )


def _negative(
    name: str,
    expected_error: str,
    state: dict[str, Any],
    profile: BiologicalProfile,
    action: Callable[[], Any],
    *,
    registry: bool = False,
    clock_unchanged: bool | None = None,
) -> dict[str, Any]:
    state_before = canonical_bytes(state)
    trace_before = canonical_bytes(profile.pending_trace)
    registry_before = tuple(profile.registry.mechanisms)
    try:
        action()
    except Exception as error:
        actual_error = type(error).__name__
    else:
        actual_error = None
    result = {
        "name": name,
        "error": actual_error,
        "expected_error": expected_error,
        "state_unchanged": canonical_bytes(state) == state_before,
        "trace_unchanged": canonical_bytes(profile.pending_trace) == trace_before,
    }
    if registry:
        result["registry_unchanged"] = tuple(profile.registry.mechanisms) == registry_before
    if clock_unchanged is not None:
        result["clock_unchanged"] = clock_unchanged
    return result


def _result(
    fixture: dict[str, Any],
    final_state: dict[str, Any],
    trace: list[dict[str, Any]],
    negatives: list[dict[str, Any]],
    assertions: dict[str, bool],
    profile: BiologicalProfile,
) -> CaseResult:
    normalized_state = canonical_state(final_state)
    normalized_trace = canonical_trace(trace)
    checks = {
        "exact_trace": normalized_trace == fixture["expected_trace"],
        "exact_final_state": normalized_state == fixture["expected_final_state"],
        "negative_errors_exact": all(
            item["error"] == item["expected_error"] for item in negatives
        ),
        "negative_state_unchanged": all(
            item.get("state_unchanged", True) for item in negatives
        ),
        "negative_trace_unchanged": all(
            item.get("trace_unchanged", True) for item in negatives
        ),
        "one_mechanism_per_runtime_node": profile.assert_one_mechanism_per_node(),
    }
    checks.update(assertions)
    return CaseResult(
        fixture=fixture["fixture"],
        target="vivarium",
        final_state=normalized_state,
        trace=normalized_trace,
        negative_results=negatives,
        assertions=checks,
        metadata={"runtime_nodes": dict(sorted(profile.runtime_nodes.items()))},
    )


class MeritAllocatorStep(GuardedStep):
    lowering_table = {"Contribution": ("proposal", "budget-proposal-projection")}
    def inputs(self):
        return {"merit_a": "string", "merit_b": "string"}

    def outputs(self):
        return {"proposal": {"A": "integer", "B": "integer", "available": "integer"}}

    def propose(self, state, interval):
        del interval
        weights = {
            "A": int(state["merit_a"]),
            "B": int(state["merit_b"]),
        }
        proposal = {"A": 2, "B": 1, "available": 3}
        effect = Contribution(
            "BudgetResolver",
            ("execution_budget",),
            "MeritAllocator",
            {"available_instructions": 3, "weights": weights},
        )
        return Proposal(
            effects=(effect,),
            trace_records=(
                {
                    "kind": "ContributionAccepted",
                    "payload": {
                        "available_instructions": 3,
                        "resolver_id": "BudgetResolver",
                        "weights": weights,
                    },
                    "source": "MeritAllocator",
                    "time": "0.0",
                },
            ),
        )


class BudgetResolverStep(GuardedStep):
    lowering_table = {"StateDelta": ("budget", "map-direct")}
    def inputs(self):
        return {"proposal": {"A": "integer", "B": "integer", "available": "integer"}}

    def outputs(self):
        return {"budget": {"A": "integer", "B": "integer"}}

    def propose(self, state, interval):
        del interval
        proposal = state["proposal"]
        if proposal.get("available") != 3:
            return Proposal(effects=())
        value = {"A": int(proposal["A"]), "B": int(proposal["B"])}
        return Proposal(
            effects=(StateDelta(("execution_budget",), "set", value),),
            trace_records=(
                {
                    "contributors": ["MeritAllocator"],
                    "kind": "ResolverCommit",
                    "source": "BudgetResolver",
                    "target_path": ["execution_budget"],
                    "time": "0.0",
                    "value": value,
                },
            ),
        )


class InstructionProcess(GuardedProcess):
    lowering_table = {"StateDelta": ("executed", "integer-count")}
    config_schema = {"mechanism_id": "string", "organism": "string"}

    def __init__(self, config=None, core=None):
        super().__init__(config=config, core=core)
        self.executions = 0
        self.elapsed = Decimal("0.0")

    def inputs(self):
        return {"budget": "integer"}

    def outputs(self):
        return {"executed": "integer"}

    def calculate_timestep(self, interval, state):
        del interval
        budget = int(state["budget"])
        if budget <= 0 or self.executions >= budget:
            return 1000.0
        return 1.0 / budget

    def propose(self, state, interval):
        del state
        self.executions += 1
        self.elapsed += Decimal(str(interval))
        organism = self.config["organism"]
        source = self.config["mechanism_id"]
        path = ("organisms", organism, "executed")
        return Proposal(
            effects=(StateDelta(path, "add", 1),),
            trace_records=(
                {
                    "effect": {"kind": "StateDelta", "operation": "add", "value": 1},
                    "kind": "InstructionExecuted",
                    "source": source,
                    "target_path": list(path),
                    "time": str(self.elapsed),
                },
            ),
        )


def _execution_profile() -> BiologicalProfile:
    profile = BiologicalProfile()
    target = ("execution_budget",)
    profile.register_mechanism(
        _spec(
            "MeritAllocator",
            plane="biological",
            role="execution allocation",
            claims=(StateClaim(target, "contribute"),),
            effects=frozenset({"Contribution"}),
        ),
        "allocator-step",
    )
    profile.register_mechanism(
        _spec(
            "BudgetResolver",
            plane="biological",
            role="budget resolution",
            claims=(StateClaim(target, "commit"),),
            effects=frozenset({"StateDelta"}),
        ),
        "resolver-step",
    )
    profile.register_resolver(
        Resolver("BudgetResolver", target, frozenset({"MeritAllocator"}), ("integer-sum",))
    )
    for organism in ("A", "B"):
        path = ("organisms", organism, "executed")
        profile.register_mechanism(
            _spec(
                f"InstructionMechanism[{organism}]",
                plane="biological",
                role="instruction execution",
                claims=(StateClaim(path, "own"),),
                effects=frozenset({"StateDelta"}),
            ),
            f"instruction-{organism}",
        )
    profile.register_mechanism(
        _spec("CycleScheduler", plane="management", role="runtime scheduling")
    )
    return profile


def run_execution_budget(*, include_negatives: bool = True) -> CaseResult:
    fixture = load_fixture("execution_budget.json")
    profile = _execution_profile()
    core = allocate_profile_core(
        ("MeritAllocatorStep", MeritAllocatorStep),
        ("BudgetResolverStep", BudgetResolverStep),
        ("InstructionProcess", InstructionProcess),
    )
    allocation_state = copy.deepcopy(fixture["initial_state"])
    allocation_state.update({
        "budget_proposal": {"A": 0, "B": 0, "available": 0},
        "allocator_node": step_node(
            "MeritAllocatorStep",
            "MeritAllocator",
            inputs={
                "merit_a": ["organisms", "A", "merit"],
                "merit_b": ["organisms", "B", "merit"],
            },
            outputs={"proposal": ["budget_proposal"]},
        ),
        "resolver_node": step_node(
            "BudgetResolverStep",
            "BudgetResolver",
            inputs={"proposal": ["budget_proposal"]},
            outputs={"budget": ["execution_budget"]},
        ),
    })
    allocation = Composite({"state": allocation_state}, core=core)
    run_composite(allocation, 0.0, profile)
    biological_state = {
        "execution_budget": copy.deepcopy(allocation.state["execution_budget"]),
        "organisms": copy.deepcopy(allocation.state["organisms"]),
    }
    for organism in ("A", "B"):
        instruction_state = copy.deepcopy(biological_state)
        instruction_state["instruction_node"] = process_node(
            "InstructionProcess",
            f"InstructionMechanism[{organism}]",
            inputs={"budget": ["execution_budget", organism]},
            outputs={"executed": ["organisms", organism, "executed"]},
            interval=1.0,
            config={"organism": organism},
        )
        instruction = Composite({"state": instruction_state}, core=core)
        run_composite(instruction, 1.0, profile)
        biological_state = {
            "execution_budget": copy.deepcopy(instruction.state["execution_budget"]),
            "organisms": copy.deepcopy(instruction.state["organisms"]),
        }
    trace = profile.take_trace()
    final_state = biological_state
    negative = {"error": "PlaneAuthorityError"}
    negatives = []
    if include_negatives:
        negative_state = copy.deepcopy(fixture["initial_state"])
        negative = _negative(
            "scheduler_state_write",
            "PlaneAuthorityError",
            negative_state,
            profile,
            lambda: profile.validate(
                "CycleScheduler",
                [StateDelta(("organisms", "A", "executed"), "add", 1)],
            ),
        )
        negatives.append(negative)
    return _result(
        fixture,
        final_state,
        trace,
        negatives,
        {
            "management_has_no_effect_authority": negative["error"] == "PlaneAuthorityError",
            "separate_instruction_mechanisms": {
                "InstructionMechanism[A]",
                "InstructionMechanism[B]",
            }.issubset(profile.registry.mechanisms),
        },
        profile,
    )


class MechanicsContributor(GuardedProcess):
    lowering_table = {"Contribution": ("position", "resolved-position-envelope")}
    config_schema = {
        "mechanism_id": "string",
        "source": "string",
        "delta": "float",
    }

    def inputs(self):
        return {}

    def outputs(self):
        return {"position": "biosim_resolved_position_v1"}

    def propose(self, state, interval):
        del state, interval
        source = self.config["source"]
        value = self.config["delta"]
        effect = Contribution(
            "MechanicsResolver", ("cells", "mother", "position"), source, value
        )
        return Proposal(
            effects=(effect,),
            trace_records=(
                {
                    "kind": "ContributionAccepted",
                    "resolver_id": "MechanicsResolver",
                    "source": source,
                    "target_path": ["cells", "mother", "position"],
                    "time": "1.0",
                    "value": value,
                },
            ),
        )


class DivisionProcess(GuardedProcess):
    lowering_table = {"StructuralRewrite": ("cells", "map-divide-structural")}
    def inputs(self):
        return {
            "cells": {
                "_type": "map",
                "_value": {"position": "float", "biomass": "float"},
            }
        }

    def outputs(self):
        return {
            "cells": {
                "_type": "map",
                "_value": {"position": "float", "biomass": "float"},
            }
        }

    def propose(self, state, interval):
        del interval
        mother = state["cells"]["mother"]
        before = {"mother": copy.deepcopy(mother)}
        after = {
            "d0": {"position": mother["position"], "biomass": mother["biomass"] / 2},
            "d1": {"position": mother["position"], "biomass": mother["biomass"] / 2},
        }
        return Proposal(
            effects=(StructuralRewrite(("cells",), before, after),),
            trace_records=(
                {
                    "after": after,
                    "before": before,
                    "kind": "StructuralRewrite",
                    "source": "DivisionMechanism",
                    "target_path": ["cells"],
                    "time": "1.0",
                },
            ),
        )


def _mechanics_profile() -> BiologicalProfile:
    profile = BiologicalProfile()
    target = ("cells", "mother", "position")
    for source in ("Adhesion", "Repulsion"):
        profile.register_mechanism(
            _spec(
                source,
                plane="biological",
                role="mechanics contribution",
                claims=(StateClaim(target, "contribute"),),
                effects=frozenset({"Contribution"}),
            ),
            f"contributor-{source}",
        )
    profile.register_mechanism(
        _spec(
            "MechanicsResolver",
            plane="biological",
            role="mechanics resolution",
            claims=(StateClaim(target, "commit"),),
            effects=frozenset({"StateDelta"}),
        ),
        "resolver-handler",
    )
    profile.register_resolver(
        Resolver(
            "MechanicsResolver",
            target,
            frozenset({"Adhesion", "Repulsion"}),
            ("complete-source-set",),
        )
    )
    profile.register_mechanism(
        _spec(
            "DivisionMechanism",
            plane="biological",
            role="lifecycle division",
            claims=(StateClaim(("cells",), "own"),),
            effects=frozenset({"StructuralRewrite"}),
        ),
        "division-process",
    )
    return profile


def _selective_disable_check() -> bool:
    profile = BiologicalProfile()
    target = ("cells", "mother", "position")
    profile.register_mechanism(
        _spec(
            "Adhesion",
            plane="biological",
            role="mechanics contribution",
            claims=(StateClaim(target, "contribute"),),
            effects=frozenset({"Contribution"}),
        ),
        "adhesion-only",
    )
    core = allocate_profile_core(("MechanicsContributor", MechanicsContributor))
    state = {
        "cells": {"mother": {"position": 1.0, "biomass": 2.0}},
        "adhesion_node": process_node(
            "MechanicsContributor",
            "Adhesion",
            inputs={},
            outputs={"position": ["cells", "mother", "position"]},
            interval=1.0,
            config={"source": "Adhesion", "delta": 2.0},
        ),
    }
    composite = Composite({"state": state}, core=core)
    run_composite(composite, 1.0, profile)
    return (
        composite.state["cells"]["mother"]["position"] == 3.0
        and len(composite.process_paths) == 1
    )


def run_coupled_mechanics_division(*, include_negatives: bool = True) -> CaseResult:
    fixture = load_fixture("coupled_mechanics_division.json")
    profile = _mechanics_profile()
    core = allocate_profile_core(
        ("MechanicsContributor", MechanicsContributor),
        ("DivisionProcess", DivisionProcess),
    )
    mechanics_state = {
        "cells": {"mother": {"position": 1.0, "biomass": 2.0}},
        "adhesion_node": process_node(
            "MechanicsContributor",
            "Adhesion",
            inputs={},
            outputs={"position": ["cells", "mother", "position"]},
            interval=1.0,
            config={"source": "Adhesion", "delta": 2.0},
        ),
        "repulsion_node": process_node(
            "MechanicsContributor",
            "Repulsion",
            inputs={},
            outputs={"position": ["cells", "mother", "position"]},
            interval=1.0,
            config={"source": "Repulsion", "delta": -0.5},
        ),
    }
    mechanics = Composite({"state": mechanics_state}, core=core)
    run_composite(mechanics, 1.0, profile)
    division_state = {
        "cells": copy.deepcopy(mechanics.state["cells"]),
        "division_node": process_node(
            "DivisionProcess",
            "DivisionMechanism",
            inputs={"cells": ["cells"]},
            outputs={"cells": ["cells"]},
            interval=1.0,
        ),
    }
    division = Composite({"state": division_state}, core=core)
    run_composite(division, 1.0, profile)
    trace = profile.take_trace()
    final_state = {"cells": copy.deepcopy(division.state["cells"])}

    negatives = []
    if include_negatives:
        negative_state = copy.deepcopy(fixture["initial_state"])
        for source in ("Adhesion", "Repulsion"):
            negatives.append(
                _negative(
                    f"{source.lower()}_direct_commit",
                    "CommitAuthorityError",
                    negative_state,
                    profile,
                    lambda source=source: profile.validate(
                        source,
                        [StateDelta(("cells", "mother", "position"), "add", 1.0)],
                    ),
                )
            )
        negatives.append(
            _negative(
                "competing_division",
                "StructuralOwnershipConflictError",
                negative_state,
                profile,
                lambda: profile.register_mechanism(
                    _spec(
                        "CompetingDivision",
                        plane="biological",
                        role="competing lifecycle",
                        claims=(StateClaim(("cells",), "own"),),
                        effects=frozenset({"StructuralRewrite"}),
                    )
                ),
                registry=True,
            )
        )
    biomass = sum(Decimal(str(cell["biomass"])) for cell in final_state["cells"].values())
    return _result(
        fixture,
        final_state,
        trace,
        negatives,
        {
            "one_atomic_resolver_commit": sum(
                item["kind"] == "ResolverCommit" for item in trace
            )
            == 1,
            "no_intermediate_position_commit": not any(
                isinstance(item.get("after"), str)
                and item["after"] in {"3.0", "0.5"}
                for item in trace
            ),
            "biomass_sum_is_2.0": biomass == Decimal("2.0"),
            "independent_contributors": (
                _selective_disable_check() if include_negatives else True
            ),
        },
        profile,
    )


class MutationRateIntervention(GuardedProcess):
    lowering_table = {"StateDelta": ("rate", "sum-float-set")}
    def inputs(self):
        return {"rate": "float"}

    def outputs(self):
        return {"rate": "float"}

    def propose(self, state, interval):
        del interval
        before = state["rate"]
        after = 0.2
        return Proposal(
            effects=(StateDelta(("parameters", "mutation_rate"), "set", after),),
            trace_records=(
                {
                    "after": after,
                    "before": before,
                    "effect": {"kind": "StateDelta", "operation": "set", "value": after},
                    "kind": "StateDeltaCommitted",
                    "source": "MutationRateIntervention",
                    "target_path": ["parameters", "mutation_rate"],
                    "time": "0.0",
                },
            ),
        )


class MutationProcess(GuardedProcess):
    lowering_table = {"StructuralRewrite": ("genome", "string-leaf-structural")}
    def inputs(self):
        return {"genome": "string"}

    def outputs(self):
        return {"genome": "string"}

    def propose(self, state, interval):
        del interval
        before = state["genome"]
        return Proposal(
            effects=(
                StructuralRewrite(("population", "p0", "genome"), before, "B"),
            ),
            trace_records=(
                {
                    "after": "B",
                    "before": before,
                    "kind": "StructuralRewrite",
                    "source": "MutationMechanism",
                    "target_path": ["population", "p0", "genome"],
                    "time": "0.0",
                },
            ),
        )


class FitnessObserverProcess(GuardedProcess):
    lowering_table = {"Event": ("genome", "noop")}
    def inputs(self):
        return {"genome": "string", "fitness": "string"}

    def outputs(self):
        return {}

    def propose(self, state, interval):
        del interval
        payload = {
            "fitness": state["fitness"],
            "genome": state["genome"],
            "organism": "p0",
        }
        return Proposal(
            effects=(Event("FitnessObserved", "FitnessObserver", payload),),
            trace_records=(
                {
                    "kind": "Event",
                    "payload": payload,
                    "source": "FitnessObserver",
                    "time": "0.0",
                    "type": "FitnessObserved",
                },
            ),
        )


class MutatingFitnessObserver(GuardedProcess):
    lowering_table = {}
    def inputs(self):
        return {
            "population": {
                "p0": {"genome": "string", "fitness": "string"}
            }
        }

    def outputs(self):
        return {}

    def propose(self, state, interval):
        del interval
        state["population"]["p0"]["genome"] = "C"
        return Proposal(effects=())


def _hook_profile() -> BiologicalProfile:
    profile = BiologicalProfile()
    profile.register_mechanism(
        _spec(
            "MutationRateIntervention",
            plane="protocol",
            role="parameter intervention",
            claims=(StateClaim(("parameters", "mutation_rate"), "own"),),
            effects=frozenset({"StateDelta"}),
        ),
        "intervention-process",
    )
    profile.register_mechanism(
        _spec(
            "MutationMechanism",
            plane="biological",
            role="heredity variation",
            claims=(StateClaim(("population", "p0", "genome"), "own"),),
            effects=frozenset({"StructuralRewrite"}),
        ),
        "mutation-process",
    )
    profile.register_mechanism(
        _spec(
            "FitnessObserver",
            plane="evidence",
            role="observation",
            claims=(StateClaim(("population",), "read"),),
            effects=frozenset({"Event"}),
        ),
        "observer-process",
    )
    return profile


def _run_one(
    state: dict[str, Any],
    profile: BiologicalProfile,
    core,
    node: dict[str, Any],
) -> dict[str, Any]:
    runtime_state = copy.deepcopy(state)
    runtime_state["mechanism_node"] = node
    composite = Composite({"state": runtime_state}, core=core)
    run_composite(composite, 1.0, profile)
    return {
        "parameters": copy.deepcopy(composite.state["parameters"]),
        "population": copy.deepcopy(composite.state["population"]),
    }


def run_hook_authority(*, include_negatives: bool = True) -> CaseResult:
    fixture = load_fixture("hook_authority.json")
    profile = _hook_profile()
    core = allocate_profile_core(
        ("MutationRateIntervention", MutationRateIntervention),
        ("MutationProcess", MutationProcess),
        ("FitnessObserverProcess", FitnessObserverProcess),
        ("MutatingFitnessObserver", MutatingFitnessObserver),
    )
    state = copy.deepcopy(fixture["initial_state"])
    state["parameters"]["mutation_rate"] = 0.1
    state = _run_one(
        state,
        profile,
        core,
        process_node(
            "MutationRateIntervention",
            "MutationRateIntervention",
            inputs={"rate": ["parameters", "mutation_rate"]},
            outputs={"rate": ["parameters", "mutation_rate"]},
            interval=1.0,
        ),
    )
    state = _run_one(
        state,
        profile,
        core,
        process_node(
            "MutationProcess",
            "MutationMechanism",
            inputs={"genome": ["population", "p0", "genome"]},
            outputs={"genome": ["population", "p0", "genome"]},
            interval=1.0,
        ),
    )
    state = _run_one(
        state,
        profile,
        core,
        process_node(
            "FitnessObserverProcess",
            "FitnessObserver",
            inputs={
                "genome": ["population", "p0", "genome"],
                "fitness": ["population", "p0", "fitness"],
            },
            outputs={},
            interval=1.0,
        ),
    )
    trace = profile.take_trace()

    negatives = []
    if include_negatives:
        alias_state = copy.deepcopy(fixture["initial_state"])
        alias_state["observer_node"] = process_node(
            "MutatingFitnessObserver",
            "FitnessObserver",
            inputs={"population": ["population"]},
            outputs={},
            interval=1.0,
        )
        alias_composite = Composite({"state": alias_state}, core=core)
        alias_state_before = canonical_bytes(alias_composite.state["population"])
        alias_trace_before = canonical_bytes(profile.pending_trace)
        try:
            run_composite(alias_composite, 1.0, profile)
        except Exception as error:
            alias_error = type(error).__name__
        else:
            alias_error = None
        negatives.append(
            {
                "name": "observer_nested_alias_mutation",
                "error": alias_error,
                "expected_error": "ReadOnlyStateError",
                "state_unchanged": canonical_bytes(alias_composite.state["population"])
                == alias_state_before,
                "trace_unchanged": canonical_bytes(profile.pending_trace)
                == alias_trace_before,
            }
        )
        negatives.append(
            _negative(
                "intervention_genome_write",
                "InterventionScopeError",
                state,
                profile,
                lambda: profile.validate(
                    "MutationRateIntervention",
                    [StateDelta(("population", "p0", "genome"), "set", "B")],
                ),
            )
        )
        negatives.append(
            _negative(
                "sixth_effect_registration",
                "UnknownEffectKindError",
                state,
                profile,
                lambda: profile.register_mechanism(
                    _spec(
                        "TeleportingMechanism",
                        plane="biological",
                        role="invalid",
                        effects=frozenset({"Teleport"}),
                    )
                ),
                registry=True,
            )
        )
    closed_union = not include_negatives or negatives[-1]["error"] == "UnknownEffectKindError"
    registry_unchanged = not include_negatives or negatives[-1]["registry_unchanged"]
    return _result(
        fixture,
        state,
        trace,
        negatives,
        {
            "observer_has_no_biological_write": not any(
                claim.permission in {"own", "commit", "contribute"}
                for claim in profile.registry.mechanisms["FitnessObserver"].claims
            ),
            "intervention_exact_scope": profile.registry.mechanisms[
                "MutationRateIntervention"
            ].claims
            == (StateClaim(("parameters", "mutation_rate"), "own"),),
            "closed_effect_union": closed_union,
            "registry_unchanged": registry_unchanged,
        },
        profile,
    )


class ReactionProcess(GuardedProcess):
    lowering_table = {"StateDelta": ("count", "integer-count"), "Event": ("count", "noop")}
    config_schema = {
        "mechanism_id": "string",
        "channel": "string",
        "intervals": {"_type": "list", "_element": "float"},
    }

    def __init__(self, config=None, core=None):
        super().__init__(config=config, core=core)
        self.cursor = 0
        self.elapsed = Decimal("0.0")

    def inputs(self):
        return {"count": "integer"}

    def outputs(self):
        return {"count": "integer"}

    def calculate_timestep(self, interval, state):
        del interval, state
        if self.cursor >= len(self.config["intervals"]):
            return 1000.0
        value = Decimal(str(self.config["intervals"][self.cursor]))
        if value <= 0:
            raise InvalidIntervalError(f"interval must be positive: {value}")
        return float(value)

    def propose(self, state, interval):
        channel = self.config["channel"]
        source = self.config["mechanism_id"]
        value = Decimal(str(self.config["intervals"][self.cursor]))
        self.cursor += 1
        self.elapsed += Decimal(str(interval))
        count = int(state["count"]) + 1
        active_profile().runtime_audit.append(
            {"stage": "draw", "source": source, "value": str(value)}
        )
        payload = {"channel": channel, "count": count}
        return Proposal(
            effects=(
                StateDelta(("counts", channel), "add", 1),
                Event("ReactionOccurred", source, payload),
            ),
            trace_records=(
                {
                    "kind": "Event",
                    "payload": payload,
                    "source": source,
                    "time": str(self.elapsed),
                    "type": "ReactionOccurred",
                },
            ),
        )


def _reaction_profile() -> BiologicalProfile:
    profile = BiologicalProfile()
    for channel in ("A", "B"):
        profile.register_mechanism(
            _spec(
                f"ReactionChannel[{channel}]",
                plane="biological",
                role="continuous-time reaction",
                claims=(StateClaim(("counts", channel), "own"),),
                effects=frozenset({"StateDelta", "Event"}),
                rng_streams=(f"intervals:{channel}",),
            ),
            f"reaction-{channel}",
        )
    return profile


def run_continuous_next_event(*, include_negatives: bool = True) -> CaseResult:
    fixture = load_fixture("continuous_next_event.json")
    profile = _reaction_profile()
    core = allocate_profile_core(("ReactionProcess", ReactionProcess))
    state = copy.deepcopy(fixture["initial_state"])
    state.update(
        {
            "reaction_a_node": process_node(
                "ReactionProcess",
                "ReactionChannel[A]",
                inputs={"count": ["counts", "A"]},
                outputs={"count": ["counts", "A"]},
                interval=1.0,
                config={"channel": "A", "intervals": [0.2, 0.5]},
            ),
            "reaction_b_node": process_node(
                "ReactionProcess",
                "ReactionChannel[B]",
                inputs={"count": ["counts", "B"]},
                outputs={"count": ["counts", "B"]},
                interval=1.0,
                config={"channel": "B", "intervals": [0.5, 0.5]},
            ),
        }
    )
    composite = Composite({"state": state}, core=core)
    run_composite(composite, 1.0, profile)
    trace = profile.take_trace()
    final_state = {"counts": copy.deepcopy(composite.state["counts"])}
    consumed = {"ReactionChannel[A]": [], "ReactionChannel[B]": []}
    for record in profile.runtime_audit:
        if record.get("stage") == "draw":
            consumed[record["source"]].append(record["value"])

    negatives = []
    if include_negatives:
        for name, value in (("zero_interval", 0.0), ("negative_interval", -0.1)):
            negative_profile = _reaction_profile()
            negative_state = {
                "counts": {"A": 0, "B": 0},
                "reaction_node": process_node(
                    "ReactionProcess",
                    "ReactionChannel[A]",
                    inputs={"count": ["counts", "A"]},
                    outputs={"count": ["counts", "A"]},
                    interval=1.0,
                    config={"channel": "A", "intervals": [value]},
                ),
            }
            negative_composite = Composite({"state": negative_state}, core=core)
            state_before = canonical_bytes(negative_composite.state["counts"])
            clock_before = negative_composite.state["global_time"]
            try:
                run_composite(negative_composite, 1.0, negative_profile)
            except Exception as error:
                actual_error = type(error).__name__
            else:
                actual_error = None
            negatives.append(
                {
                    "name": name,
                    "error": actual_error,
                    "expected_error": "InvalidIntervalError",
                    "value": str(Decimal(str(value))),
                    "state_unchanged": canonical_bytes(negative_composite.state["counts"])
                    == state_before,
                    "trace_unchanged": negative_profile.pending_trace == [],
                    "clock_unchanged": negative_composite.state["global_time"]
                    == clock_before,
                }
            )
    return _result(
        fixture,
        final_state,
        trace,
        negatives,
        {
            "exact_named_draw_consumption": consumed
            == fixture["expected_draw_consumption"],
            "minimum_due_time_order": [item["time"] for item in trace]
            == ["0.2", "0.5", "0.7", "1.0"],
            "negative_clock_unchanged": all(
                item["clock_unchanged"] for item in negatives
            ),
        },
        profile,
    )


VIVARIUM_CASES = {
    "execution_budget": run_execution_budget,
    "coupled_mechanics_division": run_coupled_mechanics_division,
    "hook_authority": run_hook_authority,
    "continuous_next_event": run_continuous_next_event,
}
