"""Domain-free declaration diff, divergence-locus, and causal-attribution
primitives (v0.3 "compare" reverse attribution).

Frozen by exloop's preregistration
`docs/science-superpowers/preregistrations/2026-08-31-newlife-compare-attribution-declarability-v2.md`
(R1/R3/R4). This module knows nothing about any specific world: it operates
on whatever frozen dataclass a caller passes as a "config" and whatever
sequence of mappings a caller passes as an "observation sequence" (a
world's `MechanismSpec` registry and `WorldRunResult.history`, or a
synthetic dataclass and a hand-written runner's output). It must not import
`newlife.mechanisms` or `newlife.adapters` (R6) and must not special-case
any field name (R4) — both are enforced by tests, not by convention alone.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, Literal, Mapping, Sequence


@dataclasses.dataclass(frozen=True, slots=True)
class DeclarationDiff:
    """The declared basis for one calibration pair (R1)."""

    registry_equal: bool
    differing_fields: tuple[str, ...]
    config_a: Any
    config_b: Any


@dataclasses.dataclass(frozen=True, slots=True)
class DivergenceLocus:
    """Where two observation sequences first diverge (R3)."""

    kind: Literal["value", "length_mismatch"]
    index: int
    tick: Any | None


FieldClassification = Literal["causal", "incidental", "unresolved"]
AggregateOutcome = Literal[
    "normal", "UNATTRIBUTED_DIVERGENCE", "MULTI_CAUSAL_OR_UNRESOLVED"
]


@dataclasses.dataclass(frozen=True, slots=True)
class AttributionResult:
    """Per-field causal classification plus the aggregate outcome (R4)."""

    per_field: Mapping[str, FieldClassification]
    aggregate: AggregateOutcome


def diff_declarations(
    registry_a: Sequence[Any],
    registry_b: Sequence[Any],
    config_a: Any,
    config_b: Any,
) -> DeclarationDiff:
    """Field-by-field diff of two declarations (R1).

    ``registry_a``/``registry_b`` are compared as opaque sequences (their
    element type's own ``__eq__`` decides structural equality — this module
    never inspects a registry element's fields by name). ``config_a``/
    ``config_b`` must be instances of the same frozen dataclass type;
    comparing configs of different types is a caller error.
    """
    if type(config_a) is not type(config_b):
        raise TypeError(
            "cannot diff configs of different types: "
            f"{type(config_a).__name__!r} vs {type(config_b).__name__!r}"
        )
    differing_fields = tuple(
        sorted(
            field.name
            for field in dataclasses.fields(config_a)
            if getattr(config_a, field.name) != getattr(config_b, field.name)
        )
    )
    registry_equal = tuple(registry_a) == tuple(registry_b)
    return DeclarationDiff(
        registry_equal=registry_equal,
        differing_fields=differing_fields,
        config_a=config_a,
        config_b=config_b,
    )


def locate_divergence(
    sequence_a: Sequence[Mapping[str, Any]],
    sequence_b: Sequence[Mapping[str, Any]],
) -> DivergenceLocus | None:
    """The first index at which two observation sequences differ (R3).

    Walks both sequences index-aligned. A value difference at a shared
    index is reported before a length mismatch is even checked, matching
    the ruling that differing lengths are reported distinctly from a
    value-divergence, not conflated with one. Returns ``None`` when the
    sequences are identical in both length and content.
    """
    shared = min(len(sequence_a), len(sequence_b))
    for index in range(shared):
        entry_a = sequence_a[index]
        if entry_a != sequence_b[index]:
            tick = entry_a.get("tick") if isinstance(entry_a, Mapping) else None
            return DivergenceLocus(kind="value", index=index, tick=tick)
    if len(sequence_a) != len(sequence_b):
        return DivergenceLocus(kind="length_mismatch", index=shared, tick=None)
    return None


def attribute_causality(
    diff: DeclarationDiff,
    history_a: Sequence[Mapping[str, Any]],
    history_b: Sequence[Mapping[str, Any]],
    runner: Callable[[Any], Sequence[Mapping[str, Any]]],
) -> AttributionResult:
    """Classify every differing field as causal, incidental, or unresolved,
    and roll the per-field classifications up into an aggregate outcome (R4).

    ``runner`` reruns a (possibly synthetic) world from a config and
    returns its observation sequence; this module never constructs a world
    itself. Every differing field is empirically rerun whenever a
    divergence exists — no field is ever classified "by elimination"
    without a rerun, because a single declared difference does not prove
    that field is the cause (the true cause could lie outside the closed
    basis entirely).
    """
    if locate_divergence(history_a, history_b) is None:
        return AttributionResult(
            per_field={field: "incidental" for field in diff.differing_fields},
            aggregate="normal",
        )

    per_field: dict[str, FieldClassification] = {}
    for field in diff.differing_fields:
        hybrid_config = dataclasses.replace(
            diff.config_b, **{field: getattr(diff.config_a, field)}
        )
        hybrid_history = runner(hybrid_config)
        if hybrid_history == history_a:
            per_field[field] = "causal"
        elif hybrid_history == history_b:
            per_field[field] = "incidental"
        else:
            per_field[field] = "unresolved"

    return AttributionResult(per_field=per_field, aggregate=_aggregate(per_field))


def _aggregate(per_field: Mapping[str, FieldClassification]) -> AggregateOutcome:
    """Roll per-field classifications into one outcome, in a fixed
    precedence order (R4): an unresolved field is checked first, because it
    means the basis is not yet known to be insufficient — declaring the
    divergence unattributed before that possibility is ruled out would be a
    premature negative conclusion.
    """
    if any(classification == "unresolved" for classification in per_field.values()):
        return "MULTI_CAUSAL_OR_UNRESOLVED"
    causal_count = sum(
        1 for classification in per_field.values() if classification == "causal"
    )
    if causal_count == 0:
        return "UNATTRIBUTED_DIVERGENCE"
    if causal_count > 1:
        return "MULTI_CAUSAL_OR_UNRESOLVED"
    return "normal"
