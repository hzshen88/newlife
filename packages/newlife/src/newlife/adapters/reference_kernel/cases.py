"""Four frozen slices expressed against the generic reference kernel."""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any, Callable

from newlife.core.contracts import (
    Contribution,
    Event,
    MechanismSpec,
    Resolver,
    StateClaim,
    StateDelta,
    StructuralRewrite,
    Transfer,
)
from newlife.core.errors import InvalidIntervalError
from newlife.conform.fixtures import load_fixture
from newlife.conform.contract.canonical_ruler import canonical_bytes, canonical_state, canonical_trace
from newlife.adapters.reference_kernel.kernel import CaseResult, ReferenceKernel


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
        schedule={"kind": "fixture-defined"},
        rng_streams=rng_streams,
        allowed_effects=effects,
        invariants=("frozen-fixture",),
    )


def _negative(
    name: str,
    expected_error: str,
    kernel: ReferenceKernel,
    action: Callable[[], Any],
    *,
    registry: bool = False,
    clock_unchanged: bool | None = None,
) -> dict[str, Any]:
    state_before = canonical_bytes(kernel.state)
    trace_before = canonical_bytes(kernel.trace)
    registry_before = tuple(kernel.registry.mechanisms)
    try:
        action()
    except Exception as error:  # typed name is itself a frozen assertion
        actual_error = type(error).__name__
    else:
        actual_error = None
    result = {
        "name": name,
        "error": actual_error,
        "expected_error": expected_error,
        "state_unchanged": canonical_bytes(kernel.state) == state_before,
        "trace_unchanged": canonical_bytes(kernel.trace) == trace_before,
    }
    if registry:
        result["registry_unchanged"] = tuple(kernel.registry.mechanisms) == registry_before
    if clock_unchanged is not None:
        result["clock_unchanged"] = clock_unchanged
    return result


def _result(
    fixture: dict[str, Any],
    kernel: ReferenceKernel,
    negatives: list[dict[str, Any]],
    extra: dict[str, bool],
) -> CaseResult:
    state = canonical_state(kernel.state)
    trace = canonical_trace(kernel.trace)
    assertions = {
        "exact_trace": trace == fixture["expected_trace"],
        "exact_final_state": state == fixture["expected_final_state"],
        "negative_errors_exact": all(
            item["error"] == item["expected_error"] for item in negatives
        ),
        "negative_state_unchanged": all(
            item.get("state_unchanged", True) for item in negatives
        ),
        "negative_trace_unchanged": all(
            item.get("trace_unchanged", True) for item in negatives
        ),
    }
    assertions.update(extra)
    return CaseResult(
        fixture=fixture["fixture"],
        target="reference",
        final_state=state,
        trace=trace,
        negative_results=negatives,
        assertions=assertions,
        metadata={},
    )


def _execution_kernel(initial_state: dict[str, Any]) -> ReferenceKernel:
    kernel = ReferenceKernel(initial_state)
    budget_path = ("execution_budget",)
    kernel.register_mechanism(
        _spec(
            "MeritAllocator",
            plane="biological",
            role="execution allocation",
            claims=(StateClaim(budget_path, "contribute"),),
            effects=frozenset({"Contribution"}),
        )
    )
    kernel.register_mechanism(
        _spec(
            "BudgetResolver",
            plane="biological",
            role="budget resolution",
            claims=(StateClaim(budget_path, "commit"),),
            effects=frozenset({"StateDelta"}),
        )
    )
    for organism in ("A", "B"):
        path = ("organisms", organism, "executed")
        kernel.register_mechanism(
            _spec(
                f"InstructionMechanism[{organism}]",
                plane="biological",
                role="instruction execution",
                claims=(StateClaim(path, "own"),),
                effects=frozenset({"StateDelta"}),
            )
        )
    kernel.register_mechanism(
        _spec(
            "CycleScheduler",
            plane="management",
            role="due mechanism selection",
        )
    )
    kernel.register_resolver(
        Resolver(
            identity="BudgetResolver",
            target_path=budget_path,
            contributors=frozenset({"MeritAllocator"}),
            invariants=("integer-budget-sum",),
        )
    )
    return kernel


def run_execution_budget(*, include_negatives: bool = True) -> CaseResult:
    fixture = load_fixture("execution_budget.json")
    kernel = _execution_kernel(fixture["initial_state"])
    contribution = Contribution(
        "BudgetResolver",
        ("execution_budget",),
        "MeritAllocator",
        {"available_instructions": 3, "weights": {"A": 2, "B": 1}},
    )
    kernel.resolve(
        "BudgetResolver",
        [contribution],
        time="0.0",
        policy=lambda _before, _items: ({"A": 2, "B": 1}, {"value": {"A": 2, "B": 1}}),
    )
    for time, organism in (("0.5", "A"), ("1.0", "A"), ("1.0", "B")):
        source = f"InstructionMechanism[{organism}]"
        path = ("organisms", organism, "executed")
        kernel.apply_batch(
            source,
            [StateDelta(path, "add", 1)],
            [
                {
                    "effect": {"kind": "StateDelta", "operation": "add", "value": 1},
                    "kind": "InstructionExecuted",
                    "source": source,
                    "target_path": list(path),
                    "time": time,
                }
            ],
        )

    negative = {"error": "PlaneAuthorityError"}
    negatives = []
    if include_negatives:
        negative_kernel = _execution_kernel(fixture["initial_state"])
        negative = _negative(
            "scheduler_state_write",
            "PlaneAuthorityError",
            negative_kernel,
            lambda: negative_kernel.apply_batch(
                "CycleScheduler",
                [StateDelta(("organisms", "A", "executed"), "add", 1)],
            ),
        )
        negatives.append(negative)
    return _result(
        fixture,
        kernel,
        negatives,
        {
            "management_has_no_effect_authority": negative["error"] == "PlaneAuthorityError",
            "separate_instruction_mechanisms": all(
                name in kernel.registry.mechanisms
                for name in ("InstructionMechanism[A]", "InstructionMechanism[B]")
            ),
        },
    )


def _mechanics_kernel(initial_state: dict[str, Any]) -> ReferenceKernel:
    kernel = ReferenceKernel(initial_state)
    position = ("cells", "mother", "position")
    for identity in ("Adhesion", "Repulsion"):
        kernel.register_mechanism(
            _spec(
                identity,
                plane="biological",
                role="mechanics contribution",
                claims=(StateClaim(position, "contribute"),),
                effects=frozenset({"Contribution"}),
            )
        )
    kernel.register_mechanism(
        _spec(
            "MechanicsResolver",
            plane="biological",
            role="mechanics resolution",
            claims=(StateClaim(position, "commit"),),
            effects=frozenset({"StateDelta"}),
        )
    )
    kernel.register_mechanism(
        _spec(
            "DivisionMechanism",
            plane="biological",
            role="lifecycle division",
            claims=(StateClaim(("cells",), "own"),),
            effects=frozenset({"StructuralRewrite"}),
        )
    )
    kernel.register_resolver(
        Resolver(
            identity="MechanicsResolver",
            target_path=position,
            contributors=frozenset({"Adhesion", "Repulsion"}),
            invariants=("complete-source-set",),
        )
    )
    return kernel


def _mechanics_policy(before: Any, items: tuple[Contribution, ...]):
    delta = sum((Decimal(str(item.value)) for item in items), Decimal("0"))
    after = Decimal(str(before)) + delta
    return str(after), {
        "after": str(after),
        "before": str(before),
        "resolved_delta": str(delta),
    }


def run_coupled_mechanics_division(*, include_negatives: bool = True) -> CaseResult:
    fixture = load_fixture("coupled_mechanics_division.json")
    kernel = _mechanics_kernel(fixture["initial_state"])
    path = ("cells", "mother", "position")
    contributions = [
        Contribution("MechanicsResolver", path, "Adhesion", "2.0"),
        Contribution("MechanicsResolver", path, "Repulsion", "-0.5"),
    ]
    kernel.resolve(
        "MechanicsResolver", contributions, time="1.0", policy=_mechanics_policy
    )
    before = copy.deepcopy(kernel.state["cells"])
    after = {
        "d0": {"biomass": "1.0", "position": "2.5"},
        "d1": {"biomass": "1.0", "position": "2.5"},
    }
    kernel.apply_batch(
        "DivisionMechanism",
        [StructuralRewrite(("cells",), before, after)],
        [
            {
                "after": after,
                "before": before,
                "kind": "StructuralRewrite",
                "source": "DivisionMechanism",
                "target_path": ["cells"],
                "time": "1.0",
            }
        ],
    )

    negatives: list[dict[str, Any]] = []
    if include_negatives:
        for source in ("Adhesion", "Repulsion"):
            negative_kernel = _mechanics_kernel(fixture["initial_state"])
            negatives.append(
                _negative(
                    f"{source.lower()}_direct_commit",
                    "CommitAuthorityError",
                    negative_kernel,
                    lambda source=source, negative_kernel=negative_kernel: negative_kernel.apply_batch(
                        source, [StateDelta(path, "add", "1.0")]
                    ),
                )
            )
        conflict_kernel = _mechanics_kernel(fixture["initial_state"])
        competing_spec = _spec(
            "CompetingDivision",
            plane="biological",
            role="competing lifecycle",
            claims=(StateClaim(("cells",), "own"),),
            effects=frozenset({"StructuralRewrite"}),
        )
        negatives.append(
            _negative(
                "competing_division",
                "StructuralOwnershipConflictError",
                conflict_kernel,
                lambda: conflict_kernel.register_mechanism(competing_spec),
                registry=True,
            )
        )
    biomass = sum(Decimal(cell["biomass"]) for cell in kernel.state["cells"].values())
    return _result(
        fixture,
        kernel,
        negatives,
        {
            "one_atomic_resolver_commit": sum(
                record["kind"] == "ResolverCommit" for record in kernel.trace
            )
            == 1,
            "no_intermediate_position_commit": not any(
                isinstance(record.get("after"), str)
                and record["after"] in {"3.0", "0.5"}
                for record in kernel.trace
            ),
            "biomass_sum_is_2.0": biomass == Decimal("2.0"),
            "independent_contributors": all(
                name in kernel.registry.mechanisms for name in ("Adhesion", "Repulsion")
            ),
        },
    )


def _hook_kernel(initial_state: dict[str, Any]) -> ReferenceKernel:
    kernel = ReferenceKernel(initial_state)
    kernel.register_mechanism(
        _spec(
            "MutationRateIntervention",
            plane="protocol",
            role="parameter intervention",
            claims=(StateClaim(("parameters", "mutation_rate"), "own"),),
            effects=frozenset({"StateDelta"}),
        )
    )
    kernel.register_mechanism(
        _spec(
            "MutationMechanism",
            plane="biological",
            role="heredity variation",
            claims=(StateClaim(("population", "p0", "genome"), "own"),),
            effects=frozenset({"StructuralRewrite"}),
        )
    )
    kernel.register_mechanism(
        _spec(
            "FitnessObserver",
            plane="evidence",
            role="observation",
            claims=(StateClaim(("population",), "read"),),
            effects=frozenset({"Event"}),
        )
    )
    return kernel


def run_hook_authority(*, include_negatives: bool = True) -> CaseResult:
    fixture = load_fixture("hook_authority.json")
    kernel = _hook_kernel(fixture["initial_state"])
    rate_path = ("parameters", "mutation_rate")
    genome_path = ("population", "p0", "genome")
    kernel.apply_batch(
        "MutationRateIntervention",
        [StateDelta(rate_path, "set", "0.2")],
        [
            {
                "after": "0.2",
                "before": "0.1",
                "effect": {"kind": "StateDelta", "operation": "set", "value": "0.2"},
                "kind": "StateDeltaCommitted",
                "source": "MutationRateIntervention",
                "target_path": list(rate_path),
                "time": "0.0",
            }
        ],
    )
    kernel.apply_batch(
        "MutationMechanism",
        [StructuralRewrite(genome_path, "A", "B")],
        [
            {
                "after": "B",
                "before": "A",
                "kind": "StructuralRewrite",
                "source": "MutationMechanism",
                "target_path": list(genome_path),
                "time": "0.0",
            }
        ],
    )
    observed = kernel.guarded_read(
        "FitnessObserver", lambda view: copy.deepcopy(view[("population",)]["p0"])
    )
    event_payload = {
        "fitness": observed["fitness"],
        "genome": observed["genome"],
        "organism": "p0",
    }
    kernel.apply_batch(
        "FitnessObserver",
        [Event("FitnessObserved", "FitnessObserver", event_payload)],
        [
            {
                "kind": "Event",
                "payload": event_payload,
                "source": "FitnessObserver",
                "time": "0.0",
                "type": "FitnessObserved",
            }
        ],
    )

    negatives = []
    if include_negatives:
        alias_kernel = _hook_kernel(fixture["initial_state"])

        def mutate_alias(view: dict[tuple[str, ...], Any]) -> None:
            view[("population",)]["p0"]["genome"] = "C"

        negatives.append(
            _negative(
                "observer_nested_alias_mutation",
                "ReadOnlyStateError",
                alias_kernel,
                lambda: alias_kernel.guarded_read("FitnessObserver", mutate_alias),
            )
        )
        scope_kernel = _hook_kernel(fixture["initial_state"])
        negatives.append(
            _negative(
                "intervention_genome_write",
                "InterventionScopeError",
                scope_kernel,
                lambda: scope_kernel.apply_batch(
                    "MutationRateIntervention", [StateDelta(genome_path, "set", "B")]
                ),
            )
        )
        union_kernel = _hook_kernel(fixture["initial_state"])
        negatives.append(
            _negative(
                "sixth_effect_registration",
                "UnknownEffectKindError",
                union_kernel,
                lambda: union_kernel.register_mechanism(
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
        kernel,
        negatives,
        {
            "observer_has_no_biological_write": not any(
                claim.permission in {"own", "commit", "contribute"}
                for claim in kernel.registry.mechanisms["FitnessObserver"].claims
            ),
            "intervention_exact_scope": kernel.registry.mechanisms[
                "MutationRateIntervention"
            ].claims
            == (StateClaim(rate_path, "own"),),
            "closed_effect_union": closed_union,
            "registry_unchanged": registry_unchanged,
        },
    )


def _reaction_kernel(initial_state: dict[str, Any]) -> ReferenceKernel:
    kernel = ReferenceKernel(initial_state)
    for channel in ("A", "B"):
        kernel.register_mechanism(
            _spec(
                f"ReactionChannel[{channel}]",
                plane="biological",
                role="continuous-time reaction",
                claims=(StateClaim(("counts", channel), "own"),),
                effects=frozenset({"StateDelta", "Event"}),
                rng_streams=(f"intervals:{channel}",),
            )
        )
    return kernel


def _validated_interval(value: str) -> Decimal:
    interval = Decimal(value)
    if interval <= 0:
        raise InvalidIntervalError(f"interval must be positive: {value}")
    return interval


def run_continuous_next_event(*, include_negatives: bool = True) -> CaseResult:
    fixture = load_fixture("continuous_next_event.json")
    kernel = _reaction_kernel(fixture["initial_state"])
    streams = {
        "A": list(fixture["expected_draw_consumption"]["ReactionChannel[A]"]),
        "B": list(fixture["expected_draw_consumption"]["ReactionChannel[B]"]),
    }
    cursor = {"A": 0, "B": 0}
    due = {channel: _validated_interval(values[0]) for channel, values in streams.items()}
    consumed = {"ReactionChannel[A]": [], "ReactionChannel[B]": []}
    while due:
        channel = min(due, key=lambda key: (due[key], f"ReactionChannel[{key}]"))
        time = due[channel]
        source = f"ReactionChannel[{channel}]"
        count = kernel.state["counts"][channel] + 1
        consumed[source].append(streams[channel][cursor[channel]])
        kernel.apply_batch(
            source,
            [
                StateDelta(("counts", channel), "add", 1),
                Event("ReactionOccurred", source, {"channel": channel, "count": count}),
            ],
            [
                {
                    "kind": "Event",
                    "payload": {"channel": channel, "count": count},
                    "source": source,
                    "time": str(time),
                    "type": "ReactionOccurred",
                }
            ],
        )
        cursor[channel] += 1
        if cursor[channel] >= len(streams[channel]):
            del due[channel]
        else:
            due[channel] = time + _validated_interval(streams[channel][cursor[channel]])

    negatives: list[dict[str, Any]] = []
    if include_negatives:
        for name, value in (("zero_interval", "0.0"), ("negative_interval", "-0.1")):
            negative_kernel = _reaction_kernel(fixture["initial_state"])
            clock = Decimal("0.0")
            negatives.append(
                _negative(
                    name,
                    "InvalidIntervalError",
                    negative_kernel,
                    lambda value=value: _validated_interval(value),
                    clock_unchanged=clock == Decimal("0.0"),
                )
            )
            negatives[-1]["value"] = value
    return _result(
        fixture,
        kernel,
        negatives,
        {
            "exact_named_draw_consumption": consumed
            == fixture["expected_draw_consumption"],
            "minimum_due_time_order": [record["time"] for record in kernel.trace]
            == ["0.2", "0.5", "0.7", "1.0"],
            "negative_clock_unchanged": all(
                item["clock_unchanged"] for item in negatives
            ),
        },
    )


def run_transfer_microfixture() -> CaseResult:
    fixture = load_fixture("effect_algebra_transfer.json")
    kernel = ReferenceKernel(fixture["initial_state"])
    source_path = ("medium", "nutrient")
    destination_path = ("cell", "energy")
    kernel.register_mechanism(
        _spec(
            "TransportMechanism",
            plane="biological",
            role="resource transport",
            claims=(
                StateClaim(source_path, "own"),
                StateClaim(destination_path, "own"),
            ),
            effects=frozenset({"Transfer"}),
        )
    )
    kernel.apply_batch(
        "TransportMechanism",
        [Transfer(source_path, destination_path, "0.25")],
        [
            {
                "amount": "0.25",
                "destination_path": list(destination_path),
                "kind": "TransferCommitted",
                "source": "TransportMechanism",
                "source_path": list(source_path),
                "time": "0.0",
            }
        ],
    )
    result = _result(
        fixture,
        kernel,
        [],
        {
            "source_plus_destination_is_2.0": Decimal(
                kernel.state["medium"]["nutrient"]
            )
            + Decimal(kernel.state["cell"]["energy"])
            == Decimal("2.0"),
            "atomic_two_path_commit": len(kernel.trace) == 1,
        },
    )
    return result


REFERENCE_CASES = {
    "execution_budget": run_execution_budget,
    "coupled_mechanics_division": run_coupled_mechanics_division,
    "hook_authority": run_hook_authority,
    "continuous_next_event": run_continuous_next_event,
}
