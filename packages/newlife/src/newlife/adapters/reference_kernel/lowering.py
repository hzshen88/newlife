"""Reference-kernel lowering: LoweredOp → kernel state application (R5 class ii).

This is the whole of the adapter's "IR → update" translation for the default
backend. It is a pure function of (LoweredOp, target state) — no mechanism
dispatch, no fixture knowledge. Unit-tested against synthetic IR; the kernel
only feeds it ops produced by `newlife.core.lowering_contract.lower_effect`.
"""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any, Mapping

from newlife.core.errors import StatePathError
from newlife.core.lowering_contract import (
    OP_ADD,
    OP_CONTRIBUTION_RESOLVE,
    OP_EVENT,
    OP_SET,
    OP_STRUCTURAL,
    OP_TRANSFER_PAIR,
    LoweredOp,
)


def get_path(state: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    cursor: Any = state
    try:
        for part in path:
            cursor = cursor[part]
    except (KeyError, TypeError) as error:
        raise StatePathError(f"missing state path: {path!r}") from error
    return cursor


def set_path(state: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    cursor: Any = state
    try:
        for part in path[:-1]:
            cursor = cursor[part]
        # Deep-copy at the write boundary: a mutable payload container must
        # not alias into committed state (R4 negative 10).
        cursor[path[-1]] = copy.deepcopy(value)
    except (KeyError, TypeError) as error:
        raise StatePathError(f"missing state path: {path!r}") from error


def _copy_path_parents(
    state: dict[str, Any], path: tuple[str, ...], copied_paths: set[tuple[str, ...]]
) -> None:
    """Copy only the nested mappings that a transaction is about to mutate.

    Reference-kernel batches still commit by replacing the root state, so
    copy-on-write preserves the old state's atomicity while avoiding a full
    deep copy of every untouched grid and organism record on every stage.
    """
    cursor: Any = state
    for index, part in enumerate(path[:-1]):
        prefix = path[: index + 1]
        try:
            child = cursor[part]
        except (KeyError, TypeError) as error:
            raise StatePathError(f"missing state path: {path!r}") from error
        if prefix not in copied_paths:
            try:
                child = copy.copy(child)
                cursor[part] = child
            except (KeyError, TypeError) as error:
                raise StatePathError(f"missing state path: {path!r}") from error
            copied_paths.add(prefix)
        cursor = child


def set_path_cow(
    state: dict[str, Any],
    path: tuple[str, ...],
    value: Any,
    copied_paths: set[tuple[str, ...]],
) -> None:
    """Set a path in a copy-on-write transaction."""
    _copy_path_parents(state, path, copied_paths)
    try:
        cursor: Any = state
        for part in path[:-1]:
            cursor = cursor[part]
        cursor[path[-1]] = copy.deepcopy(value)
    except (KeyError, TypeError) as error:
        raise StatePathError(f"missing state path: {path!r}") from error


def numeric_add(left: Any, right: Any) -> Any:
    """Addition semantics for `add` effects.

    Real-valued state requires IEEE754 binary addition (correctly rounded,
    same as any host float pipeline — this is what let the World 1
    trajectory match Julia bit-for-bit; the previous Decimal(str)-based
    accumulation rounded differently in chained sums and silently shifted
    reproduction timing). Integer state stays integral. The Decimal branch
    remains for non-numeric (string) contract semantics only.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        raise TypeError("boolean StateDelta addition is undefined")
    if isinstance(left, int) and isinstance(right, int):
        return left + right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return float(left) + float(right)
    return str(Decimal(str(left)) + Decimal(str(right)))


def apply_op(state: dict[str, Any], op: LoweredOp) -> None:
    """Apply one LoweredOp to kernel state. contribution_resolve/event are
    state-neutral here: envelopes are consumed by the Resolver lowering, and
    events carry no state semantics (frozen kernel behavior)."""
    if op.op == OP_SET:
        set_path(state, op.path, op.payload)  # payload IS the after value
    elif op.op == OP_ADD:
        before = get_path(state, op.path)
        set_path(state, op.path, numeric_add(before, op.payload))
    elif op.op == OP_TRANSFER_PAIR:
        source_before = get_path(state, op.payload["source_path"])
        destination_before = get_path(state, op.payload["destination_path"])
        amount = Decimal(str(op.payload["amount"]))
        set_path(state, op.payload["source_path"], numeric_add(source_before, -amount))
        set_path(state, op.payload["destination_path"], numeric_add(destination_before, amount))
    elif op.op == OP_STRUCTURAL:
        actual = get_path(state, op.path)
        if actual != op.payload["before"]:
            raise StatePathError(f"StructuralRewrite before mismatch at {op.path!r}")
        set_path(state, op.path, op.payload["after"])
    elif op.op in (OP_CONTRIBUTION_RESOLVE, OP_EVENT):
        return
    else:
        raise StatePathError(f"unlowerable op: {op.op!r}")


def apply_op_cow(
    state: dict[str, Any], op: LoweredOp, copied_paths: set[tuple[str, ...]]
) -> None:
    """Apply a lowered op using transactional copy-on-write semantics."""
    if op.op == OP_SET:
        set_path_cow(state, op.path, op.payload, copied_paths)
    elif op.op == OP_ADD:
        before = get_path(state, op.path)
        set_path_cow(state, op.path, numeric_add(before, op.payload), copied_paths)
    elif op.op == OP_TRANSFER_PAIR:
        source_path = op.payload["source_path"]
        destination_path = op.payload["destination_path"]
        source_before = get_path(state, source_path)
        destination_before = get_path(state, destination_path)
        amount = Decimal(str(op.payload["amount"]))
        set_path_cow(
            state, source_path, numeric_add(source_before, -amount), copied_paths
        )
        set_path_cow(
            state,
            destination_path,
            numeric_add(destination_before, amount),
            copied_paths,
        )
    elif op.op == OP_STRUCTURAL:
        actual = get_path(state, op.path)
        if actual != op.payload["before"]:
            raise StatePathError(f"StructuralRewrite before mismatch at {op.path!r}")
        set_path_cow(state, op.path, op.payload["after"], copied_paths)
    elif op.op in (OP_CONTRIBUTION_RESOLVE, OP_EVENT):
        return
    else:
        raise StatePathError(f"unlowerable op: {op.op!r}")
