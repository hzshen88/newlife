"""R2 — the core lowering semantic contract: Effect → LoweredOp IR.

The single write path (proposal v0.6 §5.2): mechanisms emit Effects only;
runtime updates are derived mechanically. Core owns the *semantic contract*
only — the intermediate representation and the pure Effect → IR mapping. The
IR → runtime-update translation is adapter knowledge (update shapes depend on
the target store's registered type semantics), separately unit-tested per
adapter (R5 diagnosability split: (i) Effect → IR vs (ii) IR → update).

Ruling R2 (frozen plan §3):
- ``LoweredOp(path, op, payload, provenance)``;
- ``op`` ∈ {set, add, transfer_pair, structural, contribution_resolve, event};
- one Effect maps to exactly one LoweredOp;
- provenance is ambient (mechanism identity supplied by the adapter wrapper),
  never an Effect field;
- ``path`` is the effect's target path (``transfer_pair`` carries both paths
  in its payload); ``payload`` is the effect's value/amount/after/payload;
- Contribution effects stop at ``contribution_resolve`` and are consumed only
  by the Resolver's lowering (R3: adapter-owned per-tick staging buffer).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newlife.core.contracts import (
    Contribution,
    Effect,
    Event,
    StateDelta,
    StructuralRewrite,
    Transfer,
)
from newlife.core.errors import SpecValidationError

OP_SET = "set"
OP_ADD = "add"
OP_TRANSFER_PAIR = "transfer_pair"
OP_STRUCTURAL = "structural"
OP_CONTRIBUTION_RESOLVE = "contribution_resolve"
OP_EVENT = "event"

LOWERED_OPS = frozenset(
    {
        OP_SET,
        OP_ADD,
        OP_TRANSFER_PAIR,
        OP_STRUCTURAL,
        OP_CONTRIBUTION_RESOLVE,
        OP_EVENT,
    }
)


@dataclass(frozen=True, slots=True)
class LoweredOp:
    path: tuple[str, ...] | None
    op: str
    payload: Any
    provenance: str


def lower_effect(effect: Effect, *, provenance: str) -> LoweredOp:
    """Pure mapping: exactly one Effect → exactly one LoweredOp.

    ``provenance`` is the ambient mechanism identity (R2). The mapping is a
    total function over the five frozen Effect kinds; anything else is a
    contract violation, not a lowering decision.
    """
    if not provenance:
        raise SpecValidationError("lowering provenance (mechanism identity) is required")
    if isinstance(effect, StateDelta):
        if effect.operation == "set":
            return LoweredOp(effect.path, OP_SET, effect.value, provenance)
        if effect.operation == "add":
            return LoweredOp(effect.path, OP_ADD, effect.value, provenance)
        raise SpecValidationError(f"unknown StateDelta operation: {effect.operation!r}")
    if isinstance(effect, Transfer):
        payload = {
            "source_path": effect.source_path,
            "destination_path": effect.destination_path,
            "amount": effect.amount,
        }
        return LoweredOp(effect.source_path, OP_TRANSFER_PAIR, payload, provenance)
    if isinstance(effect, StructuralRewrite):
        payload = {"before": effect.before, "after": effect.after}
        return LoweredOp(effect.target_path, OP_STRUCTURAL, payload, provenance)
    if isinstance(effect, Contribution):
        payload = {
            "resolver_id": effect.resolver_id,
            "source_id": effect.source_id,
            "value": effect.value,
        }
        return LoweredOp(effect.target_path, OP_CONTRIBUTION_RESOLVE, payload, provenance)
    if isinstance(effect, Event):
        payload = {"event_type": effect.event_type, "payload": effect.payload}
        return LoweredOp(None, OP_EVENT, payload, provenance)
    raise SpecValidationError(f"unknown Effect kind: {type(effect).__name__}")
