"""v0.1b staging: declaration schema validation, orchestration derivation
(R3 P1–P3), compilation, and the R6 reference-order predicate.

The staging schema lives on the free-form `schedule` field of MechanismSpec
(contract v1 dataclass shape untouched): `{"stage": <str>, "after": [<str>...]}`.
Everything in this module is a pure function of the closed basis (staging
declarations, registered specs, node wiring paths and node configs including
`interval`, declared initial state, prior committed state) — no harness
knowledge, no wall clocks, no RNG. Validation deep-copies the declaration at
the boundary, so mutating a nested `after` list afterwards cannot alter a
derived orchestration (R4 negative 5).
"""

from __future__ import annotations

import copy
import heapq
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from newlife.core.contracts import MechanismSpec
from newlife.core.errors import StageValidationError

# ---------------------------------------------------------------- declaration


def staging_declaration(spec: MechanismSpec) -> tuple[str, tuple[str, ...]]:
    """Extract (stage, after) from a spec's schedule — deep-copied at the
    validation boundary. Missing declaration is a rejection: no defaults."""
    schedule = spec.schedule
    if "stage" not in schedule or "after" not in schedule:
        raise StageValidationError(
            f"{spec.identity} has no staging declaration (defaults are not allowed)"
        )
    stage = schedule["stage"]
    if not isinstance(stage, str) or not stage:
        raise StageValidationError(f"{spec.identity}: stage must be a non-empty string")
    after = schedule["after"]
    if isinstance(after, str) or not isinstance(after, (list, tuple)):
        raise StageValidationError(f"{spec.identity}: after must be a list of stage labels")
    if any(not isinstance(entry, str) or not entry for entry in after):
        raise StageValidationError(f"{spec.identity}: after entries must be non-empty strings")
    return stage, tuple(after)  # copy: the spec's own list stays mutable


def validate_staging(
    specs: Iterable[MechanismSpec],
    node_types: Mapping[str, str] | None = None,
) -> dict[str, tuple[str, tuple[str, ...]]]:
    """R2 validation. Returns {mechanism_id: (stage, after)} as immutable
    copies. Raises StageValidationError on: missing declaration, malformed
    schema, unknown `after` reference, self-loop, cyclic DAG, or a stage
    mixing Step and Process members (when node types are supplied)."""
    declared: dict[str, tuple[str, tuple[str, ...]]] = {}
    for spec in specs:
        declared[spec.identity] = staging_declaration(spec)

    labels = {stage for stage, _ in declared.values()}
    stage_after: dict[str, set[str]] = {}
    for identity, (stage, after) in declared.items():
        for prereq in after:
            if prereq not in labels:
                raise StageValidationError(
                    f"{identity}: unknown after reference {prereq!r}"
                )
        if stage in after:
            raise StageValidationError(f"{identity}: self-loop after {stage!r}")
        stage_after.setdefault(stage, set()).update(after)
    _assert_acyclic(stage_after)

    if node_types is not None:
        members: dict[str, set[str]] = {}
        for identity, (stage, _) in declared.items():
            members.setdefault(stage, set()).add(identity)
        for stage, mechs in members.items():
            kinds = {node_types[mech] for mech in mechs}
            if len(kinds) > 1:
                raise StageValidationError(
                    f"stage {stage!r} mixes Step and Process members: {sorted(mechs)}"
                )
    return declared


def _assert_acyclic(stage_after: Mapping[str, set[str]]) -> None:
    order = topological_order(stage_after)
    if len(order) != len(stage_after):
        leftover = sorted(set(stage_after) - set(order))
        raise StageValidationError(f"staging DAG has a cycle among: {leftover}")


def topological_order(stage_after: Mapping[str, set[str]]) -> list[str]:
    """Deterministic topological order (Kahn, lexicographic tie-break)."""
    indegree = {stage: 0 for stage in stage_after}
    dependents: dict[str, list[str]] = {stage: [] for stage in stage_after}
    for stage, prereqs in stage_after.items():
        indegree[stage] = len(prereqs)
        for prereq in prereqs:
            dependents[prereq].append(stage)
    ready = [stage for stage, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        stage = heapq.heappop(ready)
        order.append(stage)
        for dependent in dependents[stage]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)
    return order


# ------------------------------------------------- R3 derivation (P1–P3)


@dataclass(frozen=True)
class StagePlan:
    label: str
    duration: float
    mechanisms: tuple[str, ...]
    state_roots: tuple[str, ...]
    internal_roots: tuple[str, ...]
    state: Mapping[str, Any]
    nodes: Mapping[str, Any]


@dataclass(frozen=True)
class Orchestration:
    plan: tuple[StagePlan, ...]
    declared: Mapping[str, tuple[str, tuple[str, ...]]]
    carried_roots: tuple[str, ...]

    def record(self) -> dict[str, Any]:
        """Programmatic P4 comparison record: stages, durations, members,
        per-stage state roots and internal roots (never eyeballed)."""
        return {
            "carried_roots": list(self.carried_roots),
            "stages": [
                {
                    "label": plan.label,
                    "duration": plan.duration,
                    "mechanisms": list(plan.mechanisms),
                    "state_roots": list(plan.state_roots),
                    "internal_roots": list(plan.internal_roots),
                }
                for plan in self.plan
            ],
        }


def _wiring_roots(node: Mapping[str, Any], key: str) -> set[str]:
    roots = set()
    for path in (node.get(key) or {}).values():
        if isinstance(path, (list, tuple)) and path:
            roots.add(path[0])
    return roots


def _schema_zero(schema: Any) -> Any:
    if schema == "integer":
        return 0
    if schema == "float":
        return 0.0
    if schema == "string":
        return ""
    if isinstance(schema, dict) and "_type" in schema and schema["_type"] == "map":
        return {}
    if isinstance(schema, dict):
        return {key: _schema_zero(value) for key, value in schema.items()}
    raise StageValidationError(f"cannot zero-initialize schema: {schema!r}")


def _recheck_mixed_stages(validated, node_types):
    members: dict[str, set[str]] = {}
    for identity, (stage, _) in validated.items():
        if identity in node_types:
            members.setdefault(stage, set()).add(identity)
    for stage, mechs in members.items():
        kinds = {node_types[mech] for mech in mechs}
        if len(kinds) > 1:
            raise StageValidationError(
                f"stage {stage!r} mixes Step and Process members: {sorted(mechs)}"
            )


def derive_orchestration(
    validated: Mapping[str, tuple[str, tuple[str, ...]]],
    nodes: Mapping[str, Mapping[str, Any]],
    initial_state: Mapping[str, Any],
    output_schemas: Mapping[tuple[str, str], Any] | None = None,
) -> Orchestration:
    """R3: pure derivation of the multi-Composite orchestration from the
    closed basis. P1 state roots, P2 durations, P3 grouping/order."""
    output_schemas = output_schemas or {}
    unknown = sorted(set(nodes) - set(validated))
    if unknown:
        raise StageValidationError(f"nodes without validated staging declarations: {unknown}")
    node_types = {mech: node.get("_type", "process") for mech, node in nodes.items()}
    # Mixed-stage guard re-checked at compile entry: node types are adapter
    # knowledge the profile cannot see; the frozen R2 error semantics
    # (StageValidationError before any run) are preserved here.
    _recheck_mixed_stages(validated, node_types)

    producers: dict[str, set[str]] = {}
    consumers: dict[str, set[str]] = {}
    producer_ports: dict[str, tuple[str, str]] = {}
    for mech, node in nodes.items():
        for port, path in (node.get("inputs") or {}).items():
            if isinstance(path, (list, tuple)) and path:
                consumers.setdefault(path[0], set()).add(mech)
        for port, path in (node.get("outputs") or {}).items():
            if isinstance(path, (list, tuple)) and path:
                producers.setdefault(path[0], set()).add(mech)
                producer_ports.setdefault(path[0], (mech, port))

    initial_roots = set(initial_state)
    stage_of = {mech: stage for mech, (stage, _) in validated.items()}
    internal: dict[str, str] = {}
    for root in sorted(set(producers) | set(consumers)):
        if root in initial_roots:
            continue
        actors = producers.get(root, set()) | consumers.get(root, set())
        if not actors:
            raise StageValidationError(
                f"root-closure: wiring root {root!r} has no producer or consumer"
            )
        owner_stages = {stage_of[mech] for mech in actors}
        if len(owner_stages) > 1:
            raise StageValidationError(
                f"root-closure: wiring root {root!r} is created across stages "
                f"{sorted(owner_stages)} and belongs to neither the initial "
                "state nor a single stage"
            )
        if not producers.get(root):
            raise StageValidationError(
                f"root-closure: wiring root {root!r} is consumed but never produced"
            )
        internal[root] = next(iter(owner_stages))

    carried_roots = tuple(sorted(initial_roots - set(internal)))
    stage_after: dict[str, set[str]] = {}
    for stage, after in validated.values():
        stage_after.setdefault(stage, set()).update(after)
    order = topological_order(stage_after)

    plans: list[StagePlan] = []
    for stage in order:
        mechs = tuple(sorted(m for m, (s, _) in validated.items() if s == stage))
        stage_internal = tuple(sorted(r for r, owner in internal.items() if owner == stage))
        state: dict[str, Any] = {root: copy.deepcopy(initial_state[root]) for root in carried_roots}
        for root in stage_internal:
            producer, port = producer_ports[root]
            schema = output_schemas.get((producer, port))
            if schema is None:
                raise StageValidationError(
                    f"internal root {root!r} has no declared output schema for "
                    f"its producer ({producer!r}, {port!r}); cannot zero-initialize"
                )
            state[root] = _schema_zero(schema)
        stage_nodes = {mech: copy.deepcopy(dict(nodes[mech])) for mech in mechs}
        steps = [m for m in mechs if stage_nodes[m].get("_type") == "step"]
        processes = [m for m in mechs if stage_nodes[m].get("_type", "process") == "process"]
        if steps and processes:
            raise StageValidationError(f"stage {stage!r} mixes Step and Process members")
        if processes:
            intervals = {stage_nodes[m].get("interval") for m in processes}
            if len(intervals) != 1 or None in intervals:
                raise StageValidationError(
                    f"stage {stage!r}: Process members disagree on interval: "
                    f"{sorted(str(item) for item in intervals)}"
                )
            duration = float(next(iter(intervals)))
        else:
            duration = 0.0  # Step-only stage: dependency-triggered
        plans.append(
            StagePlan(
                label=stage,
                duration=duration,
                mechanisms=mechs,
                state_roots=tuple(sorted(state)),
                internal_roots=stage_internal,
                state=state,
                nodes=stage_nodes,
            )
        )
    return Orchestration(
        plan=tuple(plans), declared=dict(validated), carried_roots=carried_roots
    )


def compile_staging(
    nodes: Mapping[str, Mapping[str, Any]],
    specs: Iterable[MechanismSpec],
    initial_state: Mapping[str, Any],
    output_schemas: Mapping[tuple[str, str], Any] | None = None,
) -> Orchestration:
    """Validate (R2) then derive (R3). The signature admits NO ordering
    parameter — the orchestration is a pure function of the declarations
    (R4 negative 6)."""
    validated = validate_staging(specs)
    return derive_orchestration(validated, nodes, initial_state, output_schemas)


def build_composites(orchestration: Orchestration, core) -> list[tuple[StagePlan, Any]]:
    from process_bigraph import Composite

    # Composite state keys for nodes are positional (node_0, node_1, …): the
    # engine parses state path segments, and mechanism identities contain
    # characters like '[' that must not appear in state keys. The mechanism
    # identity travels in the node's config (mechanism_id), not the key.
    built = []
    for plan in orchestration.plan:
        state = copy.deepcopy(dict(plan.state))
        for index, node in enumerate(plan.nodes.values()):
            state[f"node_{index}"] = copy.deepcopy(dict(node))
        built.append((plan, Composite({"state": state}, core=core)))
    return built


def run_orchestration(orchestration: Orchestration, profile, core) -> list[Any]:
    from process_bigraph import Composite

    from newlife.adapters.process_bigraph.wrapper import run_composite

    # State threading (the "committed state of prior stages" basis term):
    # each stage's composite is built just-in-time — its carried roots take
    # their VALUES from the previous stage's committed state (the first
    # stage uses the declared initial state). Internal roots never thread.
    composites: list[Any] = []
    current: Any = None
    for index, plan in enumerate(orchestration.plan):
        state = copy.deepcopy(dict(plan.state))
        if index > 0 and current is not None:
            for root in orchestration.carried_roots:
                state[root] = copy.deepcopy(current.state[root])
        for node_index, node in enumerate(plan.nodes.values()):
            state[f"node_{node_index}"] = copy.deepcopy(dict(node))
        composite = Composite({"state": state}, core=core)
        run_composite(composite, plan.duration, profile)
        composites.append(composite)
        current = composite
    return composites


# --------------------------------------------------- R6 reference predicate


def strict_successors(stage_after: Mapping[str, set[str]]) -> dict[str, set[str]]:
    """Transitive downstream set: stages that must run after each stage."""
    successors = {stage: set() for stage in stage_after}
    for stage in stage_after:
        frontier = [stage]
        seen: set[str] = set()
        while frontier:
            current = frontier.pop()
            for dependent, prereqs in stage_after.items():
                if current in prereqs and dependent not in seen:
                    seen.add(dependent)
                    frontier.append(dependent)
        successors[stage] = seen - {stage}
    return successors


def order_is_consistent_with_dag(
    stage_after: Mapping[str, set[str]], program_order: Iterable[str]
) -> bool:
    """R6 predicate (repetition-aware): for any two executions i < j,
    stage(i) must not be a strict DAG successor of stage(j). Equivalently,
    first occurrences form a topological order and no stage reappears after
    any of its DAG successors has begun. A checker that merely deduplicates
    before validating would wrongly accept
    [allocate, instruct-a, instruct-b, instruct-a]."""
    successors = strict_successors(stage_after)
    seq = list(program_order)
    unknown = sorted({stage for stage in seq if stage not in stage_after})
    if unknown:
        raise StageValidationError(f"program order references undeclared stages: {unknown}")
    for i in range(len(seq)):
        for j in range(i + 1, len(seq)):
            if seq[i] in successors.get(seq[j], ()):
                return False
    return True
