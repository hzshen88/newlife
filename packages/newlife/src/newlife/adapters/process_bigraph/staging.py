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
