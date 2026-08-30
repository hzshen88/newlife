"""Process-Bigraph adapter lowering: LoweredOp → engine update (R5 class ii).

The IR → runtime-update translation is adapter knowledge (proposal §5.2):
what a `set` means depends on the target store's registered type semantics.
This module is the complete, unit-testable dispatch — mechanism authors never
write engine updates (R4); they declare which (port, store type) each Effect
kind targets via the class-level ``lowering_table``, and the handlers below
do the rest as pure functions of (LoweredOp, observed state view, interval).

Handlers are keyed by store type; each returns the engine-update fragment for
its port. ``interval`` is ambient runtime context (the value the engine
legally passes into ``update``) and is used only where the frozen store type
embeds tick time (contribution envelopes).
"""

from __future__ import annotations

from typing import Any, Callable

from newlife.core.errors import SpecValidationError
from newlife.core.lowering_contract import (
    OP_CONTRIBUTION_RESOLVE,
    OP_EVENT,
    OP_SET,
    OP_STRUCTURAL,
    LoweredOp,
)

StoreHandler = Callable[[LoweredOp, str, dict[str, Any], float], dict[str, Any]]


def _integer_count(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # add on an integer store: the engine reconciles per-timestep updates by
    # summation, so the update carries the delta itself.
    return {port: op.payload}


def _map_direct(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # set on a map store whose fields are committed wholesale (budget store).
    return {port: op.payload}


def _sum_float_set(op: LoweredOp, port: str, view, _interval) -> dict[str, Any]:
    # set on a sum-reconciling float store: the engine adds the update to the
    # current value, so the set is translated to after − observed_before.
    # State-view arithmetic — class (ii) adapter translation, sanctioned by
    # the frozen prediction for MutationRateIntervention, never an H0 shape.
    return {port: op.payload - view[port]}


def _list_direct(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # set on a list store: the update is the whole new list (overwrite).
    return {port: op.payload}


def _string_leaf_structural(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # structural rewrite of a leaf string store collapses to its after value.
    return {port: op.payload["after"]}


def _map_divide_structural(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # structural rewrite of a map store with a single-key before-state is the
    # engine's division sentinel: the before key is the mother, the after
    # mapping is the daughters.
    before = op.payload["before"]
    if not isinstance(before, dict) or len(before) != 1:
        raise SpecValidationError(
            "map-divide structural rewrite requires a single-mother before state"
        )
    mother = next(iter(before))
    return {port: {"_divide": {"mother": mother, "daughters": op.payload["after"]}}}


def _budget_proposal_projection(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # Contribution envelope projected onto the proposal store's registered
    # type {A, B, available}: weights become the per-organism allocation and
    # available_instructions the budget size. Pure restructuring of the
    # effect payload — class (ii) store-type knowledge.
    if op.op != OP_CONTRIBUTION_RESOLVE:
        raise SpecValidationError("budget-proposal projection consumes Contribution ops")
    value = op.payload["value"]
    weights = value["weights"]
    return {
        port: {
            "A": weights["A"],
            "B": weights["B"],
            "available": value["available_instructions"],
        }
    }


def _resolved_position_envelope(op: LoweredOp, port: str, _view, interval) -> dict[str, Any]:
    # Contribution envelope for the registered biosim_resolved_position_v1
    # store: named provenance rides with the delta (R3; the tick time comes
    # from the engine-passed interval, not from mechanism state).
    if op.op != OP_CONTRIBUTION_RESOLVE:
        raise SpecValidationError("resolved-position envelope consumes Contribution ops")
    return {
        port: {
            "source": op.payload["source_id"],
            "delta": op.payload["value"],
            "resolver_id": op.payload["resolver_id"],
            "time": str(interval),
        }
    }


def _noop(_op: LoweredOp, _port: str, _view, _interval) -> dict[str, Any]:
    # event ops carry no state semantics: the effect is validated and traced,
    # the update contributes nothing.
    return {}


STORE_HANDLERS: dict[str, StoreHandler] = {
    "integer-count": _integer_count,
    "map-direct": _map_direct,
    "list-direct": _list_direct,
    "sum-float-set": _sum_float_set,
    "string-leaf-structural": _string_leaf_structural,
    "map-divide-structural": _map_divide_structural,
    "budget-proposal-projection": _budget_proposal_projection,
    "resolved-position-envelope": _resolved_position_envelope,
    "noop": _noop,
}


def lower_update(
    mechanism_id: str,
    lowering_table: dict[str, tuple[str, str]],
    effects: tuple,
    state_view: dict[str, Any],
    interval: float,
) -> dict[str, Any]:
    """Derive the engine update from validated Effects alone (pure function
    of Effect payloads, registered store types, mechanism identity, observed
    state view — the R5 basis). One Effect → one LoweredOp → one handler."""
    from newlife.core.lowering_contract import lower_effect

    update: dict[str, Any] = {}
    for effect in effects:
        if effect.kind not in lowering_table:
            raise SpecValidationError(
                f"{mechanism_id} has no lowering binding for Effect {effect.kind}"
            )
        port, store_type = lowering_table[effect.kind]
        handler = STORE_HANDLERS.get(store_type)
        if handler is None:
            raise SpecValidationError(f"unknown store type: {store_type!r}")
        op = lower_effect(effect, provenance=mechanism_id)
        update.update(handler(op, port, state_view, interval))
    return update
